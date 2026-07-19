"""Anti-aliased 4bpp hangul glyph renderer matching the game's dialogue font CLUT.
CLUT: index0 = transparent, index1 = darkest, higher = lighter (blends to bg).
Coverage c in [0,1] -> index: c>=~1 -> 1, c->0 -> 0 (transparent), mid -> 2..15.
Renders a 16x16 cell (8 bytes/row, 4bpp), returns bytes and pixel width.
"""
from PIL import Image, ImageFont, ImageDraw

FONT = r"D:\Works\tear\ft2-korean\font\gulim.ttc"
SS = 4  # supersample factor

def _coverage_cell(ch, size, font_path, box=16, dx=0, dy=0):
    font = ImageFont.truetype(font_path, size * SS)
    img = Image.new("L", (box * SS, box * SS), 0)
    d = ImageDraw.Draw(img)
    d.text((dx * SS, dy * SS), ch, fill=255, font=font)
    small = img.resize((box, box), Image.BOX)  # average -> coverage
    return small

def cov_to_index(c):
    """c: 0..255 coverage. -> 4bpp palette index (0 transparent, 1 darkest .. 15 lightest)."""
    if c < 24:
        return 0
    # map coverage 24..255 -> index 15..1 (more coverage = darker = lower index)
    idx = 1 + round((255 - c) / 255 * 13)
    return max(1, min(15, idx))

def render_aa(ch, size=15, box=16, dx=0, dy=0):
    """Return (glyph_bytes[128], width_px). 16x16 cell, 8 bytes/row."""
    cov = _coverage_cell(ch, size, FONT, box, dx, dy)
    px = cov.load()
    out = bytearray(box * 8)
    maxx = 0
    for y in range(box):
        for x in range(box):
            idx = cov_to_index(px[x, y])
            if idx:
                if x > maxx:
                    maxx = x
                bi = y * 8 + x // 2
                if x & 1:
                    out[bi] |= idx << 4
                else:
                    out[bi] |= idx
    width = maxx + 2 if maxx else size  # advance = ink extent + 1px gap
    return bytes(out), width

def ascii_preview(gb, box=16):
    lines = []
    for y in range(box):
        row = ""
        for x in range(box):
            bi = y * 8 + x // 2
            v = (gb[bi] >> 4) if x & 1 else (gb[bi] & 0xF)
            row += " .:-=+*#@"[min(8, v)] if v else " "
        lines.append(row)
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    for ch in (sys.argv[1] if len(sys.argv) > 1 else "루난글"):
        gb, w = render_aa(ch)
        print(f"--- {ch!r} width={w}")
        print(ascii_preview(gb))
