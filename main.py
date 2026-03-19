import argparse
import json
import os
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

    # download-piece subcommand
    dp_parser = subparsers.add_parser('download-piece', help='Download a single piece from a peer')
    add_torrent_arg(dp_parser)
    dp_parser.add_argument("piece_index", type=int, help="Index of the piece to download")
    dp_parser.add_argument("--output", "-o", type=str, default=None, help="Output file path (optional)")

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

    elif args.command == 'download-piece':
        reader, client = get_tracker_client(args.file)
        print(f"[main] piece_length = {reader.piece_length}")
        peers = client.get_peers()

        piece_data = None
        for ip, port in peers:
            try:
                print(f"[main] Trying {ip}:{port}")
                conn = PeerConnection(ip, port, reader.info_hash, client.peer_id)
                conn.connect()
                conn.send_interested()
                conn.wait_for_unchoke()
                piece_data = conn.download_piece(args.piece_index, reader.piece_length)
                conn.close()
                break
            except Exception as e:
                print(f"[main] Failed with {ip}:{port} — {e}, trying next peer...")

        if not piece_data:
            print("[main] All peers failed.")
            return

        print(f"[main] Downloaded piece {args.piece_index}: {len(piece_data)} bytes")
        output_path = args.output or f"piece_{args.piece_index}.bin"
        with open(output_path, "wb") as f:
            f.write(piece_data)
        print(f"[main] Saved to {output_path}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
