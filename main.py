import argparse
from encoder import Encoder

def main():
    print("Hello from decatorrent!")
    parser = argparse.ArgumentParser(prog='DecaTorrent',description='Encodes a text file to bencode format')
    parser.add_argument("file", type=argparse.FileType())
    args = parser.parse_args()
    print(args.file.read())
    args.file.seek(0)
    encoder = Encoder(args.file).encode()
    
if __name__ == "__main__":
    main()
