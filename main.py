import argparse
from bencoder import Bencoder


def main():
    print("Hello from decatorrent!")
    parser = argparse.ArgumentParser(prog='DecaTorrent', description='Encodes a text file to bencode format')
    parser.add_argument("file", type=argparse.FileType())
    args = parser.parse_args()
    print(args.file.read())
    args.file.seek(0)
    bencoder = Bencoder(inputfile=args.file, parsedFilePath="new-text.txt").run()

if __name__ == "__main__":
    main()
