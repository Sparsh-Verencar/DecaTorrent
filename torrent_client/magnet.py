import base64
import hashlib
import socket
from io import BytesIO
from urllib.parse import urlencode, quote

import requests

from bencoder.bencoder import Bencoder


# ---------------------------------------------------------------------------
# Magnet URI parsing
# ---------------------------------------------------------------------------

def parse_magnet(uri: str) -> tuple[bytes, str, list[str]]:
    """
    Parse a magnet URI using regex so parse_qs quirks can't break it.
    Returns (info_hash: bytes, display_name: str, trackers: list[str])
    Supports both 40-char hex and 32-char base32 info hashes.
    """
    import re
    from urllib.parse import unquote, unquote_plus

    if not uri.startswith("magnet:"):
        raise ValueError("Not a valid magnet URI")

    # ---- info hash -------------------------------------------------------
    # Match xt=urn:btih:<hash>  where <hash> is hex or base32
    xt_match = re.search(r"[?&]xt=urn(?::|%3A)btih(?::|%3A)([A-Za-z0-9]+)", uri, re.IGNORECASE)
    if not xt_match:
        raise ValueError(
            "Missing or unrecognised xt=urn:btih: parameter.\n"
            f"Raw URI: {uri}"
        )

    hash_str = xt_match.group(1)
    if len(hash_str) == 40:
        info_hash = bytes.fromhex(hash_str)
    elif len(hash_str) == 32:
        info_hash = base64.b32decode(hash_str.upper())
    else:
        raise ValueError(
            f"Unrecognised info_hash length {len(hash_str)} (expected 40-hex or 32-base32).\n"
            f"Extracted hash string: {hash_str!r}\n"
            f"Raw URI: {uri}"
        )

    # ---- display name ----------------------------------------------------
    dn_match = re.search(r"[?&]dn=([^&]+)", uri)
    name = unquote_plus(dn_match.group(1)) if dn_match else "unknown"

    # ---- trackers --------------------------------------------------------
    trackers = [unquote_plus(m.group(1)) for m in re.finditer(r"[?&]tr=([^&]+)", uri)]

    return info_hash, name, trackers


# ---------------------------------------------------------------------------
# Tracker helpers
# ---------------------------------------------------------------------------

def _get_peers_from_tracker(tracker_url: str, info_hash: bytes, peer_id: bytes) -> list[tuple[str, int]]:
    """Contact a single HTTP tracker and return compact peer list."""
    bc = Bencoder()
    params = {
        "port":       6881,
        "uploaded":   0,
        "downloaded": 0,
        "left":       0,
        "compact":    1,
        "numwant":    50,
    }
    url = (
        tracker_url
        + "?" + urlencode(params)
        + "&info_hash=" + quote(info_hash)
        + "&peer_id="   + quote(peer_id)
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    decoded = bc.decode(BytesIO(response.content))
    if b"failure reason" in decoded:
        raise Exception(f"Tracker error: {decoded[b'failure reason'].decode()}")

    raw_peers = decoded[b"peers"]
    peers = []
    for i in range(0, len(raw_peers), 6):
        chunk = raw_peers[i:i + 6]
        ip   = socket.inet_ntoa(chunk[:4])
        port = int.from_bytes(chunk[4:6], "big")
        peers.append((ip, port))
    return peers


# ---------------------------------------------------------------------------
# Metadata fetch  (BEP-9 ut_metadata over BEP-10 extension protocol)
# ---------------------------------------------------------------------------

METADATA_PIECE_SIZE = 16 * 1024   # 16 KB per BEP-9


def fetch_metadata(info_hash: bytes, trackers: list[str], peer_id: bytes) -> dict:
    """
    Contacts HTTP trackers to collect peers, then fetches the torrent info dict
    from those peers using the ut_metadata extension (BEP-9 / BEP-10).

    Returns the decoded bencode info dict (same shape as TorrentReader._extract expects).
    Raises Exception if all peers fail.
    """
    # Import here to avoid circular import (magnet ← peer ← piece_manager)
    from torrent_client.peer import PeerConnection

    # ---- 1. Gather peers from ALL HTTP(S) trackers ----
    seen_peers: set[tuple[str, int]] = set()
    peers: list[tuple[str, int]]     = []

    for tracker in trackers:
        if not tracker.startswith("http"):
            print(f"[magnet] Skipping non-HTTP tracker: {tracker}")
            continue
        try:
            print(f"[magnet] Contacting tracker: {tracker}")
            p = _get_peers_from_tracker(tracker, info_hash, peer_id)
            new = [(ip, port) for ip, port in p if (ip, port) not in seen_peers]
            seen_peers.update(new)
            peers.extend(new)
            print(f"[magnet] Got {len(new)} new peers (total {len(peers)})")
        except Exception as e:
            print(f"[magnet] Tracker failed ({tracker}): {e}")

    if not peers:
        raise Exception("Could not get peers from any tracker")

    print(f"[magnet] Total unique peers to try: {len(peers)}")

    # ---- 2. Try peers CONCURRENTLY for metadata ----
    import threading

    bc      = Bencoder()
    result  = [None]          # shared result slot
    found   = threading.Event()

    def _try_peer(ip, port):
        if found.is_set():
            return
        try:
            conn = PeerConnection(ip, port, info_hash, peer_id)
            conn.sock = __import__("socket").socket()
            conn.sock.settimeout(8)          # shorter timeout for metadata fetch
            conn.sock.connect((ip, port))
            conn.sock.sendall(conn.build_handshake())
            conn._recv_exact(68)

            conn.send_extension_handshake()
            ext_hs = conn.receive_extension_message()
            if ext_hs is None:
                conn.close()
                return

            m          = ext_hs.get(b"m", {})
            ut_id      = m.get(b"ut_metadata")
            total_size = ext_hs.get(b"metadata_size")

            if not ut_id or not total_size:
                conn.close()
                return

            num_pieces = (total_size + METADATA_PIECE_SIZE - 1) // METADATA_PIECE_SIZE
            metadata   = bytearray(total_size)

            for piece_i in range(num_pieces):
                conn.request_metadata_piece(ut_id, piece_i)
                piece_data = conn.receive_metadata_piece(ut_id)
                if piece_data is None:
                    conn.close()
                    return
                offset = piece_i * METADATA_PIECE_SIZE
                metadata[offset:offset + len(piece_data)] = piece_data

            conn.close()

            if hashlib.sha1(bytes(metadata)).digest() != info_hash:
                print(f"[magnet] {ip}:{port} metadata hash mismatch — discarding")
                return

            if not found.is_set():
                result[0] = bc.decode(BytesIO(bytes(metadata)))
                print(f"[magnet] ✓ Metadata verified! ({total_size} bytes from {ip}:{port})")
                found.set()

        except Exception as e:
            print(f"[magnet] {ip}:{port} error: {e}")

    # Launch up to 30 threads concurrently, in batches
    BATCH = 30
    for i in range(0, len(peers), BATCH):
        if found.is_set():
            break
        batch   = peers[i:i + BATCH]
        threads = [threading.Thread(target=_try_peer, args=(ip, port), daemon=True)
                   for ip, port in batch]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=12)
        if found.is_set():
            break

    if result[0] is None:
        raise Exception("Failed to fetch metadata from all available peers")

    return result[0]