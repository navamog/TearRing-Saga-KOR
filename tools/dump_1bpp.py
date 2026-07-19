"""Dump binary as 1bpp PNG (MSB-first) at given pixel width.
Usage: dump_1bpp.py <file> <out.png> <width_px> [offset_hex] [length_hex] [lsb]"""
import sys
from PIL import Image

fn, out, w = sys.argv[1], sys.argv[2], int(sys.argv[3])
off = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
d = open(fn, "rb").read()
ln = int(sys.argv[5], 16) if len(sys.argv) > 5 else len(d) - off
lsb = len(sys.argv) > 6 and sys.argv[6] == "lsb"
d = d[off:off+ln]
rows = len(d) * 8 // w
img = Image.new("1", (w, rows), 0)
px = img.load()
for i, b in enumerate(d):
    for bit in range(8):
        v = (b >> bit) & 1 if lsb else (b >> (7 - bit)) & 1
        p = i * 8 + bit
        x, y = p % w, p // w
        if y >= rows: break
        px[x, y] = v
img.save(out)
print(f"saved {out} {w}x{rows}")
