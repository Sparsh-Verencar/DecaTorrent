import argparse
import json
from bencoder import Bencoder
from bencoder.torrent_reader import TorrentReader
from torrent_client.client import TrackerClient
from torrent_client.peer import PeerConnection

def print_banner():
    banner = r"""
    ██████╗ ███████╗ ██████╗ █████╗ ████████╗ ██████╗ ██████╗ ██████╗ ███████╗███╗   ██╗████████╗
    ██╔══██╗██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗██╔══██╗██╔════╝████╗  ██║╚══██╔══╝
    ██║  ██║█████╗  ██║     ███████║   ██║   ██║   ██║██████╔╝██████╔╝█████╗  ██╔██╗ ██║   ██║   
    ██║  ██║██╔══╝  ██║     ██╔══██║   ██║   ██║   ██║██╔══██╗██╔══██╗██╔══╝  ██║╚██╗██║   ██║   
    ██████╔╝███████╗╚██████╗██║  ██║   ██║   ╚██████╔╝██║  ██║██║  ██║███████╗██║ ╚████║   ██║   
    ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   
    """
    print("\033[36m" + banner + "\033[0m")
    print("\033[90m  A BitTorrent client built from scratch.\033[0m\n")

def add_torrent_arg(parser):
    parser.add_argument("file", type=str, help="Path to .torrent file")

def get_tracker_client(torrent_path):
    reader = TorrentReader(torrent_path)
    client = TrackerClient(reader)
    return reader, client

def main():
    print_banner()

    parser = argparse.ArgumentParser(prog='DecaTorrent', description='A BitTorrent client')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('encode', help='Encode a JSON file to a .torrent file')

    decode_parser = subparsers.add_parser('decode', help='Decode a .torrent file')
    decode_parser.add_argument("file", type=argparse.FileType('rb'))

    for cmd, help_text in [
        ('read',      'Read and extract metadata from a .torrent file'),
        ('peers',     'Get peers from tracker'),
        ('handshake', 'Perform TCP handshake with a peer'),
    ]:
        add_torrent_arg(subparsers.add_parser(cmd, help=help_text))

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
        print(TorrentReader(args.file))

    elif args.command == 'peers':
        _, client = get_tracker_client(args.file)
        client.get_peers()

    elif args.command == 'handshake':
        reader, client = get_tracker_client(args.file)
        peers = client.get_peers()
        ip, port = peers[0]
        conn = PeerConnection(ip, port, reader.info_hash, client.peer_id)
        response = conn.connect()
        print(f"Handshake response: {response.hex()}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()