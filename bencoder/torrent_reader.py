from .bencoder import Bencoder

class TorrentReader:
    def __init__(self, file_path):
        self.bc = Bencoder()
        with open(file_path, "rb") as f:
            self.raw = self.bc.decode(f)  
        self._extract(self.raw)

    def _extract(self, decoded):
        self.announce = decoded[b"announce"]
        info = decoded[b"info"]
        self.name = info[b"name"]
        self.length = info[b"length"]
        self.piece_length = info[b"piece length"]
        raw_pieces = info[b"pieces"]
        self.pieces = [raw_pieces[i:i+20] for i in range(0, len(raw_pieces), 20)]
        self.info_hash = self.bc.info_hash  

    def __repr__(self):
        return (
            f"TorrentReader(\n"
            f"  announce={self.announce}\n"
            f"  name={self.name}\n"
            f"  length={self.length}\n"
            f"  piece_length={self.piece_length}\n"
            f"  num_pieces={len(self.pieces)}\n"
            f"  info_hash={self.info_hash.hex() if self.info_hash else None}\n"
            f")"
        )