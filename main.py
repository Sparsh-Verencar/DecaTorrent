import argparse
import json
import os
import threading
import time
from bencoder import Bencoder
from bencoder.torrent_reader import TorrentReader
from torrent_client.client import TrackerClient
from torrent_client.peer import PeerConnection, verify_piece
from torrent_client.piece_manager import PieceManager
from tqdm import tqdm

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

def _peer_worker(ip, port, reader, client, manager):
    tag = f"[{ip}:{port}]"
    peer_id_str = f"{ip}:{port}"
    try:
        conn = PeerConnection(ip, port, reader.info_hash, client.peer_id)
        conn.connect()

        bitfield = conn.receive_bitfield()
        if not bitfield:
            print(f"{tag} No bitfield — skipping.")
            return
        manager.update_bitfield(peer_id_str, bitfield)

        conn.send_interested()
        conn.wait_for_unchoke()

        while not manager.is_complete():
            piece_index = manager.pick_piece(peer_id=peer_id_str)
            if piece_index is None:
                time.sleep(0.5)   
                continue

            actual_length = min(
                reader.piece_length,
                reader.length - piece_index * reader.piece_length,
            )
            try:
                data = conn.download_piece(piece_index, actual_length)
                if verify_piece(data, piece_index, reader.pieces):
                    manager.write_piece(piece_index, data)
                    done = len(manager.completed)
                    total = manager.total_pieces
                    print(f"{tag} ✓ piece {piece_index}  ({done}/{total})")
                else:
                    print(f"{tag} ✗ piece {piece_index} hash mismatch — requeueing")
                    manager.requeue_piece(piece_index)
            except Exception as e:
                print(f"{tag} Error on piece {piece_index}: {e} — requeueing")
                manager.requeue_piece(piece_index)
                break   

        conn.close()

    except Exception as e:
        print(f"{tag} Connection failed: {e}")


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

    dp_parser = subparsers.add_parser('download-piece', help='Download a single piece from a peer')
    add_torrent_arg(dp_parser)
    dp_parser.add_argument("piece_index", type=int, help="Index of the piece to download")
    dp_parser.add_argument("--output", "-o", type=str, default=None, help="Output file path (optional)")

    dl_parser = subparsers.add_parser('download', help='Download the full file from peers')
    add_torrent_arg(dl_parser)
    dl_parser.add_argument("--output", "-o", type=str, default=None, help="Output file path (default: downloads/<name>)")
    dl_parser.add_argument("--max-peers", type=int, default=10, help="Max simultaneous peer connections (default: 10)")

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

        if not verify_piece(piece_data, args.piece_index, reader.pieces):
            print(f"[main] Piece {args.piece_index} FAILED verification. Discarding.")
            return
        print(f"[main] Piece {args.piece_index} verified OK.")

        output_path = args.output or f"piece_{args.piece_index}.bin"
        with open(output_path, "wb") as f:
            f.write(piece_data)
        print(f"[main] Saved to {output_path}")

    elif args.command == 'download':
        reader, client = get_tracker_client(args.file)
        peers = client.get_peers()

        name = reader.name.decode() if isinstance(reader.name, bytes) else reader.name
        output_path = args.output or os.path.join("downloads", name)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        manager = PieceManager(
            total_pieces=len(reader.pieces),
            piece_length=reader.piece_length,
            total_length=reader.length,
            output_path=output_path,
        )

        print(f"[main] Downloading '{name}' → {output_path}")
        print(f"[main] {len(reader.pieces)} pieces, {reader.piece_length} bytes each")

        selected = peers[:args.max_peers]
        print(f"[main] Spawning {len(selected)} peer thread(s)...\n")

        threads = []
        for ip, port in selected:
            t = threading.Thread(
                target=_peer_worker,
                args=(ip, port, reader, client, manager),
                daemon=True,
                name=f"peer-{ip}:{port}",
            )
            threads.append(t)
            t.start()

        done = len(manager.completed)
        total = manager.total_pieces
        with tqdm(total=total, unit="piece", desc=name, dynamic_ncols=True) as bar:
            last = 0
            while not manager.is_complete() and any(t.is_alive() for t in threads):
                done = len(manager.completed)
                total = manager.total_pieces
                print(f"  Progress: {done}/{total} pieces ({done/total*100:.1f}%)")
                time.sleep(2)
            bar.update(manager.total_pieces - last)
        for t in threads:
            t.join(timeout=5)

        if manager.is_complete():
            print(f"\n[main] ✓ Download complete! Saved to: {output_path}")
        else:
            remaining = len(manager.needed)
            print(f"\n[main] ✗ Incomplete. {remaining}/{len(reader.pieces)} pieces still missing.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()