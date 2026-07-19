"""Locate the source of the VRAM(768,256) font sheet among game files.
Font in VRAM: 4bpp, row stride 2048B (1024px*2). Extract several glyph rows,
search each file for the row bytes; if consecutive rows are contiguous (stride 128)
in a file, that file holds the sheet uncompressed."""
import gzip, struct, sys, glob, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix

state = gzip.decompress(open(r"D:\Works\tear\ePSXe1925K\sstates\SLPS_031.77.000", "rb").read())
exe = open(r"D:\Works\tear\extracted\SLPS_031.77", "rb").read()
ram_base = state.find(exe[0x800:0x800+64]) - 0x10000
VBASE = 0x2733df

def vram_row(xw, y, nwords=64):
    o = VBASE + (y*1024 + xw)*2
    return state[o:o+nwords*2]

# font at (768,256), search full 128-row height for glyph rows
rows = [vram_row(768, 256+r, 64) for r in range(0, 128)]
busy = max(range(len(rows)), key=lambda i: sum(1 for b in rows[i] if b not in (0, 0xFF)))
sig = rows[busy]
print(f"busy row {busy}, nonzero {sum(1 for b in sig if b not in (0,0xFF))}, sig head {sig[:24].hex(' ')}")

# search all extracted files + image raw
files = glob.glob(r"D:\Works\tear\extracted\**\*", recursive=True)
files = [f for f in files if os.path.isfile(f)]
for fn in files:
    d = open(fn, "rb").read()
    j = d.find(sig)
    if j >= 0:
        # verify next row contiguous at +128
        nxt = rows[busy+1] if busy+1 < len(rows) else None
        contig = bool(nxt) and d[j+128:j+128+128] == nxt
        print(f"FOUND in {os.path.relpath(fn, r'D:/Works/tear/extracted')} at 0x{j:X} contig={contig}")

# also search whole disc image raw
print("searching raw image...")
with open(r"D:\Works\tear\티어링사가(eng).img", "rb") as f:
    data = f.read()
j = data.find(sig)
print("raw image match:", hex(j) if j >= 0 else "none", "LBA", j//2352 if j>=0 else "-")
