"""PoC v3 — decisive: overwrite ASCII atlas cells 'A'(0x41)/'B'(0x42) with 한/글,
put plain ASCII 'AB' in dialogue. No bank codes, uses the proven ASCII render path.
"""
import sys, struct
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from build_poc2 import glyph_10, cell_patch_bytes
import iso_extract as ix

IMG = r"D:\Works\tear\build\tear_kr_test.img"
WINTIMS = ["/I1/WINTIM.AR", "/I1/WINTIM1.AR", "/I1/WINTIM2.AR", "/I1/WINTIM3.AR", "/I1/WINTIM4.AR"]

ix.f = open(IMG, "rb")
idx = ix.build_index()
han = cell_patch_bytes(glyph_10("한"))
geul = cell_patch_bytes(glyph_10("글"))

patches = []
for path in WINTIMS:
    lba, size, _ = idx[path]
    d = ix.read_user(lba, size)
    off = 8
    n = struct.unpack_from("<I", d, 0)[0]
    bmp_off = None
    for _ in range(n):
        esize = struct.unpack_from("<I", d, off)[0]
        name = d[off+4:off+20].split(b"\x00")[0]
        end = struct.unpack_from("<I", d, off+20)[0]
        if name == b"1A_BMP.TIM":
            bmp_off = end - esize
            break
        off += 24
    px = bmp_off + 64
    for code, rows in ((0x41, han), (0x42, geul)):
        u = (code % 25) * 10
        v = (code // 25) * 10
        for dy in range(10):
            patches.append((lba, px + (v + dy) * 128 + u // 2, rows[dy]))
    print(f"{path}: cells 0x41/0x42 -> 한/글")
ix.f.close()

# GEVMSG08.MES: replace "What's the matter?" region with plain ASCII "AB"+spaces
# original at +0x52A: 00 5D 01 05 20 6d 61 74 74 65 72 3f  (part of "...spaced" no—this is the matter line)
# we already overwrote +0x52A..+0x53C in v2; now write clean: "AB" then spaces, keep 00 70 00 10 delimiters intact after.
patches.append((232173, 0x52A, b"AB" + b" " * 16))  # 18 bytes = original "What's the matter?" length
apply(IMG, patches)
print("PoC v3 built.")
