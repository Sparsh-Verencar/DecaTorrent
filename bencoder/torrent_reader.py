from .bencoder import Bencoder


class TorrentReader:
    def __init__(self, file_path):
        self.bc = Bencoder()
        with open(file_path, "rb") as f:
            self.raw = self.bc.decode(f)
        self._extract(self.raw)

    def _extract(self, decoded):
        self.announce    = decoded[b"announce"].decode("utf-8")
        info             = decoded[b"info"]
        self.name        = info[b"name"]
        self.length      = info[b"length"]
        self.piece_length = info[b"piece length"]
        raw_pieces       = info[b"pieces"]
        self.pieces      = [raw_pieces[i:i + 20] for i in range(0, len(raw_pieces), 20)]
        self.info_hash   = self.bc.info_hash

    # ------------------------------------------------------------------
    # Alternative constructor — build from an already-decoded info dict
    # (used by the magnet-link flow after fetching ut_metadata)
    # ------------------------------------------------------------------

    @classmethod
    def from_info_dict(cls, info_dict: dict, info_hash: bytes, announce: str = "") -> "TorrentReader":
        """
        Construct a TorrentReader without a .torrent file.

        Parameters
        ----------
        info_dict : dict
            Bencode-decoded info dictionary fetched via ut_metadata (BEP-9).
        info_hash : bytes
            20-byte SHA-1 hash of the bencoded info dict (from the magnet URI).
        announce : str
            Tracker URL (first entry from the magnet &tr= list, or empty string).
        """
        obj              = cls.__new__(cls)
        obj.announce     = announce
        obj.name         = info_dict[b"name"]
        obj.length       = info_dict[b"length"]
        obj.piece_length = info_dict[b"piece length"]
        raw_pieces       = info_dict[b"pieces"]
        obj.pieces       = [raw_pieces[i:i + 20] for i in range(0, len(raw_pieces), 20)]
        obj.info_hash    = info_hash
        return obj

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