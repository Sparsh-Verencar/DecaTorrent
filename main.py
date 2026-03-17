import argparse
import json
from bencoder import Bencoder
from bencoder.torrent_reader import TorrentReader
from torrent_client.client import TrackerClient

def main():
    print("Hello from DecaTorrent!")
    parser = argparse.ArgumentParser(prog='DecaTorrent', description='A BitTorrent client')
    subparsers = parser.add_subparsers(dest='command')
    
    peers_parser = subparsers.add_parser('peers', help='Get peers from tracker')
    peers_parser.add_argument("file", type=str, help="Path to .torrent file")

    subparsers.add_parser('encode', help='Encode a JSON file to a .torrent file')
    
    decode_parser = subparsers.add_parser('decode', help='Decode a .torrent file')
    decode_parser.add_argument("file", type=argparse.FileType('rb'))

    read_parser = subparsers.add_parser('read', help='Read and extract metadata from a .torrent file')
    read_parser.add_argument("file", type=str)  

    args = parser.parse_args()
    bc = Bencoder()

    if args.command == 'encode':
        with open("text.txt", "r") as f:
            data = json.load(f)
        encoded = bc.encode(data)
        with open(".torrent", "wb") as f:
            f.write(encoded)
        print("Encoded and written to .torrent")

    elif args.command == 'decode':
        result = bc.decode(args.file)
        print("Decoded result:", result)
        with open("new-text.txt", "w") as f:
            f.write(str(result))
        if bc.info_hash:
            print("info_hash:", bc.info_hash.hex())

    elif args.command == 'read':
        reader = TorrentReader(args.file)
        print(reader)
        
    elif args.command == "peers":
        torrent = TorrentReader(args.file)
        client = TrackerClient(torrent)
        client.get_peers()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
