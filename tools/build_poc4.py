"""PoC v4 — overwrite 'A'/'B' glyphs inside the REAL embedded font block of
GEVMSG08.MES (the opening ship scene's dialogue file). VRAM-confirmed source.

Font block in GEVMSG08.MES at file offset 0x2BD8: 256x96 4bpp, row stride 128B.
Grid: 16px cells, 16 cols. char C -> col=(C-0x20)%16, row=(C-0x20)//16.
Cell (col,row): x=col*16 px (=col*8 bytes), y=row*16 rows within block.
Glyph 16x16 4bpp = 16 rows x 8 bytes. Stroke nibble = 0xF (white in CLUT[15]? use 1..15).
"""
import sys, struct
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from render_glyph import render_glyph
import iso_extract as ix

IMG = r"D:\Works\tear\build\tear_kr_test.img"
MES_LBA = 232173           # GEVMSG08.MES relocated LBA
FONT_OFF = 0x2BD8          # font block start in file
STROKE = 0x1   # glyph body index (original font uses 1 as the dark body color)

def glyph16_4bpp_rows(ch):
    """16 rows x 8 bytes, 4bpp, stroke=STROKE. render_glyph gives 15x15 -> pad to 16."""
    rows15 = render_glyph(ch, size=16, dy=0)  # 15 rows of 15-bit masks
    out = []
    for y in range(16):
        b = bytearray(8)
        if y < 15:
            h = rows15[y]
            for x in range(16):
                on = (h >> (15 - x)) & 1 if x < 15 else 0
                if on:
                    if x & 1:
                        b[x // 2] |= STROKE << 4
                    else:
                        b[x // 2] |= STROKE
        out.append(bytes(b))
    return out

def cell_patches(ch, code):
    col = (code - 0x20) % 16
    row = (code - 0x20) // 16
    x_byte = col * 8       # 16px -> 8 bytes
    y0 = row * 16
    rows = glyph16_4bpp_rows(ch)
    ps = []
    for dy in range(16):
        fo = FONT_OFF + (y0 + dy) * 128 + x_byte
        ps.append((MES_LBA, fo, rows[dy]))
    return ps

patches = []
patches += cell_patches("한", 0x41)  # 'A'
patches += cell_patches("글", 0x42)  # 'B'
# text already "AB" from v3 at +0x52A
apply(IMG, patches)
print("PoC v4 built: 'A'->한 'B'->글 in embedded font of GEVMSG08.MES")
