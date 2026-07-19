"""Find bytes >=0x80 inside MES text records (how does eng patch encode extended glyphs?)."""
import sys, struct, collections
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix

IMG = r"D:\Works\tear\티어링사가(eng).img"
ix.f = open(IMG, "rb")
idx = ix.build_index()

hist = collections.Counter()
samples = []
mes_files = [(k, v) for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2]
for name, (lba, size, _) in mes_files:
    d = ix.read_user(lba, size)
    if d[:4] != b"ESMD":
        continue
    off = 4
    while off + 8 <= len(d):
        rsize, rid = struct.unpack_from("<II", d, off)
        if rsize == 0 or off + 8 + rsize > len(d):
            break
        pl = d[off+8:off+8+rsize]
        # skip the leading config prelude records (size 12)
        i = 0
        while i < len(pl):
            b = pl[i]
            if b >= 0x80:
                # skip known arg contexts: preceded by 00 5X/2X opcodes? keep raw sample
                hist[b] += 1
                if len(samples) < 25:
                    samples.append((name, rid, i, pl[max(0,i-14):i+10]))
            i += 1
        off += 8 + rsize

print("bytes >=0x80 in text records:", sum(hist.values()))
for b, n in hist.most_common(20):
    print(f"  {b:02X}: {n}")
print()
for name, rid, i, ctx in samples:
    print(f"{name} id={rid} +0x{i:X}: {ctx.hex(' ')} | {ctx!r}")
