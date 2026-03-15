from .encoder import Encoder
from .decoder import Decoder

class Bencoder:
    def __init__(self):
        self.encoder = Encoder()
        self.decoder = Decoder()

    def encode(self, data):
        return self.encoder.encode(data)

    def decode(self, file):
        return self.decoder.decode(file)

    @property
    def info_hash(self):
        return self.decoder.info_hash