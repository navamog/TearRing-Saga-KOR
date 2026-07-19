"""PoC v2 — pure-data hangul test (no code hooks).

- Overwrite atlas cells 0x180/0x181 (kanji cells, row 15 col 9/10) in 1A_BMP.TIM
  of every WINTIM*.AR with '한'/'글' 10x10 glyphs (stroke=index F, bg=0).
- Re-encode probe text in GEVMSG08.MES: bank1 select + bytes 80,81.
  bytes: 00 41 80 81 00 40 20 20 20 20  (replaces earlier 10-byte probe at +0x52A)

Atlas cell math: code C -> col=C%25, row=C//25, u=col*10, v=row*10.
1A_BMP.TIM pixel data: TIM +64 (8 hdr + 44 CLUT + 12 pixel hdr), row stride 128B.
4bpp: low nibble = left pixel of byte pair.
"""
import sys, struct
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from render_glyph import render_glyph
import iso_extract as ix

IMG = r"D:\Works\tear\build\tear_kr_test.img"
WINTIMS = ["/I1/WINTIM.AR", "/I1/WINTIM1.AR", "/I1/WINTIM2.AR", "/I1/WINTIM3.AR", "/I1/WINTIM4.AR"]

HAND = {
    "한": [
        "..#.....#.",
        ".#####..#.",
        "........#.",
        "..###...##",
        ".#...#..#.",
        "..###...#.",
        ".#......#.",
        ".#........",
        ".#####....",
        "..........",
    ],
    "글": [
        ".######...",
        "......#...",
        "......#...",
        ".########.",
        "..........",
        ".######...",
        "......#...",
        ".######...",
        ".#........",
        ".######...",
    ],
}

def glyph_10(ch):
    """10x10 binary glyph rows (hand-drawn dot font for PoC)."""
    return [[1 if c == "#" else 0 for c in row] for row in HAND[ch]]

def cell_patch_bytes(grid):
    """Per-row 5-byte sequences for a 10px-wide 4bpp cell (stroke=0xF)."""
    rows = []
    for y in range(10):
        b = bytearray(5)
        for x in range(10):
            v = 0xF if grid[y][x] else 0
            if x & 1:
                b[x // 2] |= v << 4
            else:
                b[x // 2] |= v
        rows.append(bytes(b))
    return rows

def main():
    ix.f = open(IMG, "rb")
    idx = ix.build_index()
    han = cell_patch_bytes(glyph_10("한"))
    geul = cell_patch_bytes(glyph_10("글"))

    patches = []
    for path in WINTIMS:
        lba, size, _ = idx[path]
        d = ix.read_user(lba, size)
        n, _hdr = struct.unpack_from("<II", d, 0)
        off = 8
        bmp_off = None
        for _ in range(n):
            esize = struct.unpack_from("<I", d, off)[0]
            name = d[off+4:off+20].split(b"\x00")[0]
            end = struct.unpack_from("<I", d, off+20)[0]
            if name == b"1A_BMP.TIM":
                bmp_off = end - esize
                break
            off += 24
        if bmp_off is None:
            print(f"{path}: no 1A_BMP.TIM, skipped")
            continue
        px = bmp_off + 64
        for code, rows in ((0x180, han), (0x181, geul), (0x141, han), (0x142, geul)):
            u = (code % 25) * 10
            v = (code // 25) * 10
            for dy in range(10):
                fo = px + (v + dy) * 128 + u // 2
                patches.append((lba, fo, rows[dy]))
        print(f"{path}: 1A_BMP.TIM at 0x{bmp_off:X}, cells patched")
    ix.f.close()

    # probe C: bank1 + bytes 80,81 (codes 0x180/0x181) -- tests >=0x80 bytes under bank
    patches.append((232173, 0x52A, bytes.fromhex("00418081004020202020")))
    # probe D: bank1 + bytes 41,42 (codes 0x141/0x142) -- tests <0x80 bytes under bank
    # replaces original " matter?" (8 bytes at +0x534)
    patches.append((232173, 0x534, bytes.fromhex("0041414200402020")))
    apply(IMG, patches)

if __name__ == "__main__":
    main()
