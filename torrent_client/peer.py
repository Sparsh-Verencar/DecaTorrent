import socket
import struct
import hashlib
from torrent_client.piece_manager import PieceManager

MSG_CHOKE = 0
MSG_UNCHOKE = 1
MSG_INTERESTED = 2
MSG_BITFIELD = 5
MSG_REQUEST = 6
MSG_PIECE = 7

BLOCK_SIZE = 2 ** 14  # 16KB


class PeerConnection:
    def __init__(self, ip, port, info_hash, peer_id):
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.sock = None
        self.am_choked = True

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
        self.sock.settimeout(10)
        try:
            self.sock.connect((self.ip, self.port))
            self.sock.sendall(self.build_handshake())
            return self._recv_exact(68)  # handshake response is always 68 bytes
        except Exception as e:
            raise ValueError(f"Could not create socket connection: {e}")


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
        length = struct.unpack(">I", raw_len)[0]
        if length == 0:
            return None  # keep-alive
        msg_id = self._recv_exact(1)[0]
        payload = self._recv_exact(length - 1) if length > 1 else b""
        return {"id": msg_id, "payload": payload}

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
                data = msg["payload"][8:]
                return index, begin, data
            elif msg["id"] == MSG_CHOKE:
                raise ConnectionError("Peer re-choked us during download")

    def download_all(self, piece_manager: PieceManager, pieces_hashes, piece_length):
        while not piece_manager.is_complete():
            piece_index = piece_manager.pick_piece(peer_id=self.peer_id)
            if piece_index is None:
                break  

            total_length = piece_manager.total_length
            actual_length = min(piece_length, total_length - piece_index * piece_length)

            data = self.download_piece(piece_index, actual_length)

            if verify_piece(data, piece_index, pieces_hashes):
                piece_manager.write_piece(piece_index, data)
            else:
                print(f"[!] Piece {piece_index} failed verification, requeueing")
                piece_manager.requeue_piece(piece_index)
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
    
    
    def close(self):
        if self.sock:
            self.sock.close()
            
def verify_piece(piece_data: bytes, piece_index: int, pieces: list) -> bool:
    expected_hash = pieces[piece_index]
    actual_hash = hashlib.sha1(piece_data).digest()
    return actual_hash == expected_hash