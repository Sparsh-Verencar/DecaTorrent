import socket
import struct
import hashlib
from io import BytesIO
from torrent_client.piece_manager import PieceManager

MSG_CHOKE       = 0
MSG_UNCHOKE     = 1
MSG_INTERESTED  = 2
MSG_BITFIELD    = 5
MSG_REQUEST     = 6
MSG_PIECE       = 7
MSG_EXTENDED    = 20   # BEP-10

EXT_HANDSHAKE_ID = 0   # extension handshake always uses ext_id = 0

BLOCK_SIZE = 2 ** 14   # 16 KB


class PeerConnection:
    def __init__(self, ip, port, info_hash, peer_id):
        self.ip        = ip
        self.port      = port
        self.info_hash = info_hash
        self.peer_id   = peer_id
        self.sock      = None
        self.am_choked = True

    # ------------------------------------------------------------------
    # Handshake
    # ------------------------------------------------------------------

    def build_handshake(self):
        # Set reserved byte[5] bit-4 = extension protocol (BEP-10)
        reserved = bytearray(8)
        reserved[5] |= 0x10
        return (
            bytes([19]) +
            b"BitTorrent protocol" +
            bytes(reserved) +
            self.info_hash +
            self.peer_id
        )

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.sock.connect((self.ip, self.port))
            self.sock.sendall(self.build_handshake())
            return self._recv_exact(68)   # handshake response is always 68 bytes
        except Exception as e:
            raise ValueError(f"Could not create socket connection: {e}")

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Peer disconnected")
            buf += chunk
        return buf

    def send_message(self, msg_id, payload=b""):
        length = 1 + len(payload)
        self.sock.sendall(struct.pack(">I", length) + bytes([msg_id]) + payload)

    def receive_message(self):
        raw_len = self._recv_exact(4)
        length  = struct.unpack(">I", raw_len)[0]
        if length == 0:
            return None   # keep-alive
        msg_id  = self._recv_exact(1)[0]
        payload = self._recv_exact(length - 1) if length > 1 else b""
        return {"id": msg_id, "payload": payload}

    # ------------------------------------------------------------------
    # Standard peer-wire messages
    # ------------------------------------------------------------------

    def receive_bitfield(self) -> bytes | None:
        try:
            msg = self.receive_message()
            if msg and msg["id"] == MSG_BITFIELD:
                return msg["payload"]
            return None
        except Exception:
            return None

    def send_interested(self):
        self.send_message(MSG_INTERESTED)
        print("[PeerConnection] Sent interested")

    def wait_for_unchoke(self):
        while self.am_choked:
            msg = self.receive_message()
            if msg is None:
                continue
            if msg["id"] == MSG_UNCHOKE:
                self.am_choked = False
                print("[PeerConnection] Unchoked!")
            elif msg["id"] == MSG_BITFIELD:
                print("[PeerConnection] Received bitfield (ignored for now)")
            elif msg["id"] == MSG_CHOKE:
                print("[PeerConnection] Choked.")

    def send_request(self, piece_index, begin, length):
        payload = struct.pack(">III", piece_index, begin, length)
        self.send_message(MSG_REQUEST, payload)
        print(f"[PeerConnection] Sent request: piece={piece_index} begin={begin} length={length}")

    def receive_piece(self):
        while True:
            msg = self.receive_message()
            if msg is None:
                continue
            print(f"[PeerConnection] Received message id={msg['id']}")
            if msg["id"] == MSG_PIECE:
                index = struct.unpack(">I", msg["payload"][0:4])[0]
                begin = struct.unpack(">I", msg["payload"][4:8])[0]
                data  = msg["payload"][8:]
                return index, begin, data
            elif msg["id"] == MSG_CHOKE:
                raise ConnectionError("Peer re-choked us during download")

    def download_piece(self, piece_index, piece_length):
        piece_data = b""
        downloaded = 0
        while downloaded < piece_length:
            block_length = min(BLOCK_SIZE, piece_length - downloaded)
            self.send_request(piece_index, downloaded, block_length)
            _, _, block = self.receive_piece()
            piece_data += block
            downloaded += len(block)
            print(f"[PeerConnection] Progress: {downloaded}/{piece_length} bytes")
        return piece_data

    def download_all(self, piece_manager: PieceManager, pieces_hashes, piece_length):
        while not piece_manager.is_complete():
            piece_index = piece_manager.pick_piece(peer_id=self.peer_id)
            if piece_index is None:
                break
            total_length  = piece_manager.total_length
            actual_length = min(piece_length, total_length - piece_index * piece_length)
            data = self.download_piece(piece_index, actual_length)
            if verify_piece(data, piece_index, pieces_hashes):
                piece_manager.write_piece(piece_index, data)
            else:
                print(f"[!] Piece {piece_index} failed verification, requeueing")
                piece_manager.requeue_piece(piece_index)

    def close(self):
        if self.sock:
            self.sock.close()

    # ------------------------------------------------------------------
    # BEP-10  Extension Protocol
    # ------------------------------------------------------------------

    def send_extension_handshake(self):
        """Send our extension handshake advertising ut_metadata support."""
        from bencoder.bencoder import Bencoder
        bc      = Bencoder()
        payload = bc.encode({b"m": {b"ut_metadata": 1}, b"v": b"DecaTorrent"})
        self.send_message(MSG_EXTENDED, bytes([EXT_HANDSHAKE_ID]) + payload)

    def receive_extension_message(self, max_attempts: int = 30) -> dict | None:
        """
        Drain incoming messages until we get the peer's extension handshake
        (MSG_EXTENDED with ext_id=0).  Other messages are silently skipped.
        Returns the decoded bencode dict, or None on timeout.
        """
        from bencoder.bencoder import Bencoder
        bc = Bencoder()
        for _ in range(max_attempts):
            msg = self.receive_message()
            if msg is None:
                continue
            if msg["id"] == MSG_EXTENDED:
                ext_id = msg["payload"][0]
                if ext_id == EXT_HANDSHAKE_ID:
                    return bc.decode(BytesIO(msg["payload"][1:]))
        return None

    # ------------------------------------------------------------------
    # BEP-9  ut_metadata
    # ------------------------------------------------------------------

    def request_metadata_piece(self, ut_metadata_id: int, piece_index: int):
        """Send a ut_metadata request for one 16 KB metadata piece."""
        from bencoder.bencoder import Bencoder
        bc      = Bencoder()
        payload = bc.encode({b"msg_type": 0, b"piece": piece_index})
        self.send_message(MSG_EXTENDED, bytes([ut_metadata_id]) + payload)

    def receive_metadata_piece(self, ut_metadata_id: int, max_attempts: int = 30) -> bytes | None:
        """
        Wait for a ut_metadata data response (msg_type=1).
        Returns the raw piece bytes, or None if the peer rejects it.
        """
        from bencoder.bencoder import Bencoder
        bc = Bencoder()
        for _ in range(max_attempts):
            msg = self.receive_message()
            if msg is None:
                continue
            if msg["id"] != MSG_EXTENDED:
                continue
            ext_id = msg["payload"][0]
            if ext_id != ut_metadata_id:
                continue
            # payload[1:] = bencoded dict  +  raw piece bytes
            f         = BytesIO(msg["payload"][1:])
            meta_dict = bc.decode(f)
            msg_type  = meta_dict.get(b"msg_type")
            if msg_type == 2:   # reject
                return None
            if msg_type == 1:   # data
                return f.read()
        return None


# ---------------------------------------------------------------------------
# Standalone helper
# ---------------------------------------------------------------------------

def verify_piece(piece_data: bytes, piece_index: int, pieces: list) -> bool:
    expected_hash = pieces[piece_index]
    actual_hash   = hashlib.sha1(piece_data).digest()
    return actual_hash == expected_hash