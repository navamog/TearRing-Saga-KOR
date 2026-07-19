"""Parse ESMD .MES record structure. Validate record walk covers whole file."""
import struct, sys, os

def parse(path):
    d = open(path, "rb").read()
    assert d[:4] == b"ESMD", f"{path}: bad magic {d[:4]!r}"
    off = 4
    recs = []
    ok = True
    while off + 8 <= len(d):
        size, rid = struct.unpack_from("<II", d, off)
        if size == 0 or off + 8 + size > len(d):
            break
        recs.append((off, size, rid, d[off+8:off+8+size]))
        off += 8 + size
    tail = d[off:]
    return recs, off, len(d), tail

def preview_text(payload):
    out = []
    i = 0
    while i < len(payload):
        b = payload[i]
        if b == 0:
            if i + 1 < len(payload):
                op = payload[i+1]
                out.append(f"<{op:02X}>")
                i += 2
            else:
                out.append("<END>")
                i += 1
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            i += 1
        else:
            out.append(f"[{b:02X}]")
            i += 1
    return "".join(out)

if __name__ == "__main__":
    for path in sys.argv[1:]:
        recs, consumed, total, tail = parse(path)
        print(f"=== {os.path.basename(path)}: {len(recs)} records, consumed {consumed}/{total}, tail={len(tail)}B")
        if tail and any(tail):
            print("  tail nonzero head:", tail[:32].hex(' '))
        for off, size, rid, pl in recs[:6]:
            print(f"  @0x{off:05X} size={size:5d} id={rid:5d}  {preview_text(pl)[:110]}")
