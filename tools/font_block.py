"""Reconstruct the VRAM font sheet as a contiguous 4bpp block and locate it in files."""
import gzip, struct, sys, glob, os
sys.path.insert(0, r"D:\Works\tear\tools")
from PIL import Image

state = gzip.decompress(open(r"D:\Works\tear\ePSXe1925K\sstates\SLPS_031.77.000", "rb").read())
VBASE = 0x2733df

def vram_bytes(xw, y, nwords):
    o = VBASE + (y*1024 + xw)*2
    return state[o:o+nwords*2]

# grab font page0: (768,256) width 128 words(512px? no, 64 words=256px), height 256 rows
# render to confirm extent
sp = r"C:\Users\neokl\AppData\Local\Temp\claude\D--Works-tear\d9a29a20-62a7-4351-9309-1431c070df24\scratchpad"
def render4(xw, y, ww, h, out):
    img = Image.new("L", (ww*4, h)); p = img.load()
    for r in range(h):
        row = vram_bytes(xw, y+r, ww)
        for c in range(ww):
            v = struct.unpack_from("<H", row, c*2)[0]
            for k in range(4):
                p[c*4+k, r] = ((v >> (k*4)) & 0xF) * 17
    img.save(out)
    return out

render4(768, 256, 64, 200, f"{sp}\\font_full.png")  # 256px x 200 rows

# reconstruct contiguous block: 64 words * N rows, contiguous 128B/row
def block(xw, y, ww, h):
    out = bytearray()
    for r in range(h):
        out += vram_bytes(xw, y+r, ww)
    return bytes(out)

# try to find where glyphs start/end vertically
nz_rows = []
for r in range(256):
    row = vram_bytes(768, 256+r, 64)
    nz = sum(1 for b in row if b not in (0, 0xFF))
    nz_rows.append(nz)
first = next((r for r in range(256) if nz_rows[r] > 2), 0)
last = next((r for r in range(255, -1, -1) if nz_rows[r] > 2), 0)
print(f"glyph rows span {first}..{last}")

blk = block(768, 256+first, 64, last-first+1)
print(f"font block {len(blk)} bytes")

files = [f for f in glob.glob(r"D:\Works\tear\extracted\**\*", recursive=True) if os.path.isfile(f)]
mes_hits = 0
for fn in files:
    d = open(fn, "rb").read()
    j = d.find(blk)
    if j >= 0:
        rel = os.path.relpath(fn, r"D:/Works/tear/extracted")
        print(f"FULL BLOCK in {rel} at 0x{j:X}")
        mes_hits += 1
print(f"total files with full font block: {mes_hits}")
