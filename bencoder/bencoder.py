from .encoder import Encoder
from .decoder import Decoder

class Bencoder:
    def __init__(self, inputfile, parsedFilePath):
        self.inputfile = inputfile
        self.parsedFilePath = parsedFilePath
        self.torrent = ".torrent"
        self.encoder = Encoder()
        self.decoder = Decoder(self.parsedFilePath)
    
    def run(self):
        self.encoder.encode(self.inputfile)
        with open(self.torrent, "r") as f:
            self.decoder.decode(f)