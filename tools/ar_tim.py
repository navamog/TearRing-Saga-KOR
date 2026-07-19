"""Parse WINTIM-style .AR (u32 count; entries: u32 size + name[16] + u32 offset) and decode TIMs to PNG.
Usage: ar_tim.py <file.AR> [list|extract <name> <out.png>]"""
import struct, sys
from PIL import Image

def parse_ar(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 0)[0]
    entries = []
    off = 8
    for _ in range(n):
        size = struct.unpack_from("<I", d, off)[0]
        name = d[off+4:off+20].split(b"\x00")[0].decode("ascii", "replace")
        end = struct.unpack_from("<I", d, off+20)[0]
        entries.append((name, end - size, size))
        off += 24
    return d, entries

def tim_to_png(tim, out):
    magic, flags = struct.unpack_from("<II", tim, 0)
    assert magic == 0x10, f"not TIM: {magic:#x}"
    bpp = flags & 3
    has_clut = flags & 8
    off = 8
    clut = None
    if has_clut:
        blen, cx, cy, cw, ch = struct.unpack_from("<IHHHH", tim, off)
        ncol = cw * ch
        clut = [struct.unpack_from("<H", tim, off + 12 + i*2)[0] for i in range(ncol)]
        off += blen
    blen, px, py, pw, ph = struct.unpack_from("<IHHHH", tim, off)
    data = tim[off+12: off+blen]
    def c15(v):
        r = (v & 31) << 3; g = ((v >> 5) & 31) << 3; b = ((v >> 10) & 31) << 3
        return (r, g, b)
    if bpp == 0:  # 4bpp
        w = pw * 4
        img = Image.new("RGB", (w, ph))
        p = img.load()
        for i, byte in enumerate(data[:pw*2*ph]):
            for k, idx in ((0, byte & 0xF), (1, byte >> 4)):
                x = (i*2 + k) % w
                y = (i*2 + k) // w
                if y < ph:
                    p[x, y] = c15(clut[idx]) if clut else (idx*17,)*3
    elif bpp == 1:  # 8bpp
        w = pw * 2
        img = Image.new("RGB", (w, ph))
        p = img.load()
        for i, byte in enumerate(data[:pw*2*ph]):
            x = i % w; y = i // w
            if y < ph:
                p[x, y] = c15(clut[byte]) if clut else (byte,)*3
    else:  # 16bpp
        w = pw
        img = Image.new("RGB", (w, ph))
        p = img.load()
        for i in range(min(pw*ph, len(data)//2)):
            v = struct.unpack_from("<H", data, i*2)[0]
            p[i % w, i // w] = c15(v)
    img.save(out)
    print(f"{out}: bpp_code={bpp} frame=({px},{py}) {pw}x{ph} (px_w={img.width})")

if __name__ == "__main__":
    d, entries = parse_ar(sys.argv[1])
    if len(sys.argv) < 3 or sys.argv[2] == "list":
        for name, off, size in entries:
            print(f"{off:8X} {size:8X} {name}")
    else:
        name, out = sys.argv[2], sys.argv[3]
        for n, off, size in entries:
            if n == name:
                tim_to_png(d[off:off+size], out)
                break
        else:
            print("not found")
