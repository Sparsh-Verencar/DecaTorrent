import argparse

def encode(file):
    unencoded_file = file
    with open(".torrent", "wb") as f:
        for line in unencoded_file.readlines():
            line = line.strip()
            if line.isdigit():
                f.write((f"i{line}e").encode("utf-8"))
                continue
            elif line.startswith("[") and line.endswith("]"):
                inner = line[1:-1]  
                items = [item.strip() for item in inner.split(",")]
                f.write(("l").encode("utf-8"))
                for token in items:
                    if token.isdigit():
                        f.write((f"i{token}e").encode("utf-8"))
                    else:
                        f.write((f"{len(token)}:{token}").encode("utf-8"))
                f.write(("e").encode("utf-8"))
                continue
            elif line.startswith("{") and line.endswith("}"):
                inner = line[1:-1] 
                pairs = [p.strip() for p in inner.split(',')] 
                d = dict()
                for pair in pairs:
                    k, v = pair.split(':')
                    d[k.strip()] = v.strip()
                f.write(b'd')
                for key in sorted(d.keys()): 
                    value = d[key]
                    f.write(f"{len(key)}:".encode('utf-8') + key.encode('utf-8'))
                    if value.isdigit():
                        f.write(f"i{value}e".encode('utf-8'))
                    else:
                        f.write(f"{len(value)}:".encode('utf-8') + value.encode('utf-8'))
                f.write(b'e')
                continue
            else:
                f.write((f"{len(line)}:{line}").encode("utf-8"))
                continue
    pass

def main():
    print("Hello from decatorrent!")
    parser = argparse.ArgumentParser(prog='DecaTorrent',description='Encodes a text file to bencode format')
    parser.add_argument("file", type=argparse.FileType())
    args = parser.parse_args()
    print(args.file.read())
    args.file.seek(0)
    encode(args.file)
    
if __name__ == "__main__":
    main()
