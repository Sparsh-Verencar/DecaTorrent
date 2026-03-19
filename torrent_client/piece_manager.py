import os
import threading
from collections import defaultdict

class PieceManager:
    def __init__(self, total_pieces: int, piece_length: int, total_length: int, output_path: str):
        self.total_pieces = total_pieces
        self.piece_length = piece_length
        self.total_length = total_length
        self.output_path = output_path

        self.needed = set(range(total_pieces))        
        self.in_progress = set()                      
        self.completed = set()                        
        self.peer_bitfields: dict[str, set[int]] = {} 

        self._lock = threading.Lock()                 


    def update_bitfield(self, peer_id: str, bitfield: bytes):
        pieces = set()
        for byte_index, byte in enumerate(bitfield):
            for bit_index in range(8):
                piece_index = byte_index * 8 + (7 - bit_index)
                if piece_index < self.total_pieces and (byte >> bit_index) & 1:
                    pieces.add(piece_index)
        with self._lock:
            self.peer_bitfields[peer_id] = pieces

    def record_have(self, peer_id: str, piece_index: int):
        with self._lock:
            self.peer_bitfields.setdefault(peer_id, set()).add(piece_index)


    def pick_piece(self, peer_id: str) -> int | None:
        
        with self._lock:
            peer_has = self.peer_bitfields.get(peer_id, set())
            candidates = (self.needed - self.in_progress) & peer_has

            if not candidates:
                return None

            rarity: dict[int, int] = defaultdict(int)
            for pieces in self.peer_bitfields.values():
                for piece in candidates:
                    if piece in pieces:
                        rarity[piece] += 1

            rarest = min(candidates, key=lambda p: rarity[p])
            self.in_progress.add(rarest)
            return rarest

    def requeue_piece(self, piece_index: int):
        with self._lock:
            self.in_progress.discard(piece_index)


    def write_piece(self, piece_index: int, data: bytes):
        self._ensure_file()
        offset = piece_index * self.piece_length

        with open(self.output_path, "r+b") as f:
            f.seek(offset)
            f.write(data)

        with self._lock:
            self.in_progress.discard(piece_index)
            self.needed.discard(piece_index)
            self.completed.add(piece_index)
        print(f"[✓] Piece {piece_index} written ({len(self.completed)}/{self.total_pieces})")

    def is_complete(self) -> bool:
        with self._lock:
            return len(self.completed) == self.total_pieces

    def _ensure_file(self):
        if not os.path.exists(self.output_path):
            os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
            with open(self.output_path, "wb") as f:
                f.seek(self.total_length - 1)
                f.write(b"\x00")