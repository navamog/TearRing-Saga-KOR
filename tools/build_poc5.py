"""PoC v5 — inject hangul into the embedded font's page1 (empty), encode with bank1.
Decisive test of the code-free page1 path.

Font block in GEVMSG08.MES: page0 @0x1bd8, page1 @0x9bd8, metric @0xdbd8 (0x180).
page0 glyph sub-block starts at +0x1000 (=0x2bd8), so page1 mirror = 0x9bd8+0x1000 = 0xabd8.
Cell for code C on a page: row=(C_low-0x20)//16, col=(C_low-0x20)%16, 16x16px (8 bytes wide).
Bank1 char: text bytes `00 41` set bank=0x100, then byte B -> code 0x100|B, renders from page1.
metric[code] = advance width.
"""
import sys, struct
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from render_glyph import render_glyph
import iso_extract as ix

IMG = r"D:\Works\tear\build\tear_kr_test.img"
MES_LBA = 232173
PAGE1_GLYPH = 0xABD8   # page1 base 0x9bd8 + 0x1000 (mirror of page0's 0x2bd8)
METRIC = 0xDBD8
STROKE = 0x1

def glyph16(ch):
    rows15 = render_glyph(ch, size=16, dy=0)
    out = []
    for y in range(16):
        b = bytearray(8)
        if y < 15:
            h = rows15[y]
            for x in range(16):
                if x < 15 and (h >> (15 - x)) & 1:
                    if x & 1:
                        b[x // 2] |= STROKE << 4
                    else:
                        b[x // 2] |= STROKE
        out.append(bytes(b))
    return out

def cell_patches(ch, low):
    """low = low byte (0x20..0x7F); page1 code = 0x100|low."""
    col = (low - 0x20) % 16
    row = (low - 0x20) // 16
    rows = glyph16(ch)
    ps = [(MES_LBA, PAGE1_GLYPH + (row*16 + dy)*128 + col*8, rows[dy]) for dy in range(16)]
    return ps

patches = []
patches += cell_patches("한", 0x41)   # code 0x141
patches += cell_patches("글", 0x42)   # code 0x142
# metric widths for 0x141, 0x142
patches.append((MES_LBA, METRIC + 0x141, bytes([16])))
patches.append((MES_LBA, METRIC + 0x142, bytes([16])))
# text: bank1 + 0x41 0x42 + bank0, pad. original "What's the matter?" was 18 bytes at +0x52A.
patches.append((MES_LBA, 0x52A, bytes.fromhex("004141420040") + b" " * 12))
apply(IMG, patches)
print("PoC v5 built: page1 hangul via bank1 (code 0x141/0x142)")
