import socket

class PeerConnection:
    def __init__(self, ip, port, info_hash, peer_id):
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.sock = None
        pass

    def build_handshake(self):
        return (
            bytes([19]) +
            b"BitTorrent protocol" +
            b"\x00" * 8 +
            self.info_hash +
            self.peer_id
        )

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip, self.port))
            self.sock.send(self.build_handshake())
            return self.sock.recv(68)
        except Exception as e:
            raise ValueError(f"Could not create soccket connection: {e}")