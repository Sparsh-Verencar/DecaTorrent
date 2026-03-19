<div align="center">

```
██████╗ ███████╗ ██████╗ █████╗ ████████╗ ██████╗ ██████╗ ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗██╔══██╗██╔════╝████╗  ██║╚══██╔══╝
██║  ██║█████╗  ██║     ███████║   ██║   ██║   ██║██████╔╝██████╔╝█████╗  ██╔██╗ ██║   ██║   
██║  ██║██╔══╝  ██║     ██╔══██║   ██║   ██║   ██║██╔══██╗██╔══██╗██╔══╝  ██║╚██╗██║   ██║   
██████╔╝███████╗╚██████╗██║  ██║   ██║   ╚██████╔╝██║  ██║██║  ██║███████╗██║ ╚████║   ██║   
╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝
```

**A BitTorrent client built from scratch in Python.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

---

DecaTorrent is a fully functional BitTorrent client implemented from the ground up in Python — no libtorrent, no shortcuts. Every layer is hand-rolled: bencode parsing, tracker communication, the peer wire protocol, SHA-1 piece verification, rarest-first piece selection, and concurrent multi-peer downloading via threads.

Built as a learning project to deeply understand how BitTorrent works under the hood.

---

## Features

- **Bencode encoder/decoder** — full recursive implementation supporting strings, integers, lists, and dicts
- **Torrent file reader** — parses `.torrent` metadata and computes the `info_hash` from scratch
- **HTTP tracker client** — sends compliant announce requests, parses compact peer lists
- **Peer wire protocol** — TCP handshake, bitfield parsing, interested/unchoke/request/piece message flow
- **SHA-1 piece verification** — every piece is verified against the torrent's hash list before being written
- **Rarest-first piece selection** — `PieceManager` tracks peer bitfields and picks the globally rarest available piece
- **Concurrent downloading** — spawns one thread per peer (up to N), all sharing a thread-safe `PieceManager`
- **Progress bar** — live terminal progress via `tqdm`
- **Pre-allocated output file** — seeks and writes pieces at the correct byte offset, no reassembly needed

---

## Project Structure

```
DecaTorrent/
│
├── bencoder/
│   ├── encoder.py          # Recursive bencode encoder
│   ├── decoder.py          # Recursive bencode decoder
│   ├── bencoder.py         # Bencoder facade (encode + decode)
│   └── torrent_reader.py   # Parses .torrent files, computes info_hash
│
├── torrent_client/
│   ├── client.py           # TrackerClient — announce requests, peer list parsing
│   ├── peer.py             # PeerConnection — TCP handshake, wire protocol, piece download
│   └── piece_manager.py    # PieceManager — rarest-first selection, thread-safe state, disk I/O
│
├── main.py                 # CLI entry point
└── pyproject.toml
```

---

## How It Works

### The BitTorrent Pipeline

```
.torrent file
     │
     ▼
TorrentReader  ──►  info_hash, piece hashes, announce URL, file length
     │
     ▼
TrackerClient  ──►  HTTP GET /announce  ──►  compact peer list [(ip, port), ...]
     │
     ▼
PeerConnection (×N threads)
     │
     ├── TCP connect
     ├── Handshake  (pstrlen + "BitTorrent protocol" + reserved + info_hash + peer_id)
     ├── Receive bitfield
     ├── Send Interested
     ├── Wait for Unchoke
     └── Loop:
           pick_piece()  ──►  request block(s)  ──►  receive piece
                │
                ▼
           verify_piece()  (SHA-1 hash check)
                │
                ▼
           write_piece()  (seek to offset, write to pre-allocated file)
```

### Rarest-First Selection

`PieceManager.pick_piece(peer_id)` finds pieces that:
1. Are still needed (not in progress or completed)
2. The requesting peer has (per its bitfield)
3. Are owned by the fewest peers globally (rarest)

This maximises piece diversity across the swarm — the core insight behind BitTorrent's efficiency.

### Thread Safety

All mutations to `needed`, `in_progress`, `completed`, and `peer_bitfields` are protected by a `threading.Lock`. Disk writes happen outside the lock (I/O is slow), with state updates locked immediately after.

---

## Installation

Requires Python 3.11+ and [`uv`](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/Sparsh-Verencar/DecaTorrent.git
cd DecaTorrent
uv sync
```

---

## Usage

### Download a torrent
```bash
uv run main.py download path/to/file.torrent
uv run main.py download path/to/file.torrent -o output/path
uv run main.py download path/to/file.torrent --max-peers 5
```

### Download a single piece (debug)
```bash
uv run main.py download-piece path/to/file.torrent 0
uv run main.py download-piece path/to/file.torrent 42 -o piece_42.bin
```

### Inspect a torrent file
```bash
uv run main.py read path/to/file.torrent
```

### Fetch peers from tracker
```bash
uv run main.py peers path/to/file.torrent
```

### TCP handshake with a peer
```bash
uv run main.py handshake path/to/file.torrent
```

### Bencode utilities
```bash
uv run main.py encode
uv run main.py decode path/to/file.torrent
```

---

## Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Bencode encoder/decoder, `.torrent` file reader | ✅ Done |
| 2 | HTTP tracker requests, compact peer list parsing | ✅ Done |
| 3 | TCP handshake, peer wire protocol, single piece download | ✅ Done |
| 4 | SHA-1 verification, rarest-first selection, disk writes | ✅ Done |
| 5 | Concurrent multi-peer downloading with threading | ✅ Done |
| 6 | Choking/unchoking (tit-for-tat) | ⬜ Planned |
| 7 | Seeding | ⬜ Planned |
| 8 | Resume incomplete downloads | ⬜ Planned |
| 9 | Magnet links + DHT (BEP-0005) | ⬜ Planned |
| 10 | UDP tracker (BEP-0015) | ⬜ Planned |

---

## Key BEPs Implemented

- [BEP-0003](https://www.bittorrent.org/beps/bep_0003.html) — The BitTorrent Protocol Specification (core)

---

## Tech Stack

- **Python 3.11+** — core language
- **`requests`** — HTTP tracker communication
- **`tqdm`** — terminal progress bar
- **`threading`** — concurrent peer connections
- **`hashlib`** — SHA-1 piece verification
- **`socket`** — raw TCP peer connections
- **`uv`** — package and environment management

---

## Verified Working On

- `debian-13.4.0-amd64-netinst.iso` — 754 MB, 3016 pieces

---

<div align="center">
  Built from scratch by <a href="https://github.com/Sparsh-Verencar">Sparsh Verencar</a>
</div>
