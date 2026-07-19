"""Dump a binary region as 4bpp indexed PNG at a given pixel width for visual font hunting.
Usage: dump_4bpp.py <file> <out.png> [width_px] [offset_hex] [length_hex]"""
import sys
from PIL import Image

fn, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 256
off = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
d = open(fn, "rb").read()
ln = int(sys.argv[5], 16) if len(sys.argv) > 5 else len(d) - off
d = d[off:off+ln]
rows = len(d) * 2 // w
img = Image.new("L", (w, rows), 0)
px = img.load()
for i, b in enumerate(d):
    p0, p1 = b & 0xF, b >> 4
    x = (i * 2) % w
    y = (i * 2) // w
    if y >= rows: break
    px[x, y] = p0 * 17
    if x + 1 < w:
        px[x + 1, y] = p1 * 17
img.save(out)
print(f"saved {out} {w}x{rows}")
