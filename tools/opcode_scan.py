"""Histogram of file-level control opcodes (00 XX) across MES text records,
with context samples for chosen opcodes."""
import sys, struct, collections
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_parse import parse

import glob, os

IMG = r"D:\Works\tear\티어링사가(eng).img"
ix.f = open(IMG, "rb")
idx = ix.build_index()

hist = collections.Counter()
samples = collections.defaultdict(list)
WATCH = set(range(0x40, 0x50))

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
        i = 0
        while i < len(pl) - 1:
            if pl[i] == 0:
                op = pl[i+1]
                hist[op] += 1
                if op in WATCH and len(samples[op]) < 6:
                    ctx = pl[max(0,i-12):i+14]
                    samples[op].append((name, rid, ctx))
                i += 2
            else:
                i += 1
        off += 8 + rsize

print("opcode histogram (top 40):")
for op, n in hist.most_common(40):
    print(f"  00 {op:02X}: {n}")
print()
for op in sorted(samples):
    print(f"=== 00 {op:02X} samples:")
    for name, rid, ctx in samples[op]:
        print(f"  {name} id={rid}: {ctx.hex(' ')}  | {ctx!r}")
