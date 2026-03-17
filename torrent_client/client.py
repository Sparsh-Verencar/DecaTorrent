import os
import socket
from urllib.parse import urlencode, quote
from io import BytesIO

import requests

from bencoder.bencoder import Bencoder
from bencoder.torrent_reader import TorrentReader


class TrackerClient:
    def __init__(self, torrent: TorrentReader):
        self.torrent = torrent
        self.bencoder = Bencoder()
        self.peer_id = b'-DC0001-' + os.urandom(12)  # DC = DecaTorrent

    def _build_url(self) -> str:
        params = {
            "port":6881,
            "uploaded": 0,
            "downloaded": 0,
            "left": self.torrent.length,
            "compact": 1,
        }
        return (
            self.torrent.announce
            + "?" + urlencode(params)
            + "&info_hash=" + quote(self.torrent.info_hash)
            + "&peer_id=" + quote(self.peer_id)
        )

    def _parse_peers(self, raw_peers: bytes) -> list:
        peers = []
        for i in range(0, len(raw_peers), 6):
            chunk = raw_peers[i:i+6]
            ip = socket.inet_ntoa(chunk[:4])
            port = int.from_bytes(chunk[4:6], "big")
            peers.append((ip, port))
        return peers

    def get_peers(self) -> list:
        url = self._build_url()
        print(f"[TrackerClient] Requesting: {url}\n")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        decoded = self.bencoder.decode(BytesIO(response.content))

        if b"failure reason" in decoded:
            raise Exception(f"Tracker error: {decoded[b'failure reason'].decode()}")

        raw_peers = decoded[b"peers"]
        peers = self._parse_peers(raw_peers)

        print(f"[TrackerClient] Found {len(peers)} peers:")
        for ip, port in peers:
            print(f"  {ip}:{port}")

        return peers