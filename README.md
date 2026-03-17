# 🌊 DecaTorrent(readme in progress)

A BitTorrent client built from scratch in Python — no `libtorrent`, no shortcuts.

DecaTorrent implements the BitTorrent protocol spec (BEP-0003) piece by piece, from bencode parsing all the way to downloading files from real peers over TCP.

---

## Features

- ✅ Bencode encoder & decoder
- ✅ `.torrent` file parser (extracts metadata, `info_hash`, file tree)
- ✅ HTTP tracker communication (compact peer list parsing)
- 🔄 TCP peer handshake *(in progress)*
- ⬜ Peer message parsing & piece downloading
- ⬜ SHA-1 piece verification & disk writes
- ⬜ Multi-peer concurrent downloading
- ⬜ Tit-for-tat choking/unchoking
- ⬜ Seeding, resume, magnet links *(planned)*

---

## Project Structure

```
DecaTorrent/
├── bencoder/
│   ├── encoder.py         # Bencode encoder
│   ├── decoder.py         # Bencode decoder
│   ├── bencoder.py        # Facade class: Bencoder
│   └── torrent_reader.py  # Parses .torrent files, computes info_hash
│
├── torrent_client/
│   ├── client.py          # TrackerClient — HTTP GET to tracker, peer list parsing
│   └── peer.py            # PeerConnection — TCP handshake, peer messages (WIP)
│
└── main.py                # CLI entry point
```

---

## CLI Usage

```bash
# Encode a value to bencode
python main.py encode "hello"

# Decode a bencoded string
python main.py decode "5:hello"

# Read and display metadata from a .torrent file
python main.py read path/to/file.torrent

# Fetch peer list from tracker
python main.py peers path/to/file.torrent
```

---

## Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Bencode + `.torrent` parser | ✅ Done |
| 2 | HTTP tracker → peer list | ✅ Done |
| 3 | TCP handshake + peer messages + piece download | 🔄 In Progress |
| 4 | Piece selection, SHA-1 verification, disk writes | ⬜ Pending |
| 5 | Multi-peer concurrency, tit-for-tat | ⬜ Pending |
| 6 | Seeding, resume, magnet links, UDP tracker | ⬜ Planned |

---

## Getting Started

### Prerequisites

- Python 3.10+
- No external dependencies for core functionality *(standard library only so far)*

### Installation

```bash
git clone https://github.com/yourusername/DecaTorrent.git
cd DecaTorrent
```

### Run

```bash
python main.py peers path/to/file.torrent
```

---

## How It Works

### Bencode

BitTorrent uses a custom serialization format called **bencode**. DecaTorrent implements a full encoder and decoder from scratch, handling all four bencode types: integers, byte strings, lists, and dictionaries.

### Tracker Communication

On receiving a `.torrent` file, DecaTorrent extracts the `info_hash` (SHA-1 of the bencoded `info` dictionary) and sends an HTTP GET request to the tracker. The tracker responds with a compact binary peer list, which is parsed into `(ip, port)` tuples.

### Peer Protocol *(in progress)*

Each peer connection begins with a 68-byte handshake:

```
[pstrlen: 1 byte] [pstr: 19 bytes] [reserved: 8 bytes] [info_hash: 20 bytes] [peer_id: 20 bytes]
```

After a successful handshake, peers exchange messages to negotiate piece transfers.

---

## Spec References

- [BEP-0003 — BitTorrent Protocol](https://www.bittorrent.org/beps/bep_0003.html)
- [BEP-0015 — UDP Tracker Protocol](https://www.bittorrent.org/beps/bep_0015.html)
- [BEP-0005 — DHT Protocol (Magnet Links)](https://www.bittorrent.org/beps/bep_0005.html)

---

## License

MIT
