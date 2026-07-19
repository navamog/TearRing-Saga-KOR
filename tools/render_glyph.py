"""Render hangul glyphs to 15x15 1bpp in PS1 BIOS Krom2RawAdd format.

Format (confirmed from SLPS-03177 renderer at 0x80016F2C):
  30 bytes/glyph = 15 rows x u16 stored big-endian [hi][lo].
  bit15 = leftmost pixel, bits 15..1 = 15 pixels, bit0 = 0.
"""
from PIL import Image, ImageFont, ImageDraw

FONT = r"D:\Works\tear\ft2-korean\font\gulim.ttc"

def render_glyph(ch, size=15, font_path=FONT, threshold=128, dx=0, dy=0):
    font = ImageFont.truetype(font_path, size)
    img = Image.new("L", (16, 16), 0)
    d = ImageDraw.Draw(img)
    d.text((dx, dy), ch, fill=255, font=font)
    rows = []
    for y in range(15):
        h = 0
        for x in range(15):
            if img.getpixel((x, y)) >= threshold:
                h |= 1 << (15 - x)
        rows.append(h)
    return rows

def to_bytes(rows):
    out = bytearray()
    for h in rows:
        out += bytes([(h >> 8) & 0xFF, h & 0xFF])
    return bytes(out)

def ascii_art(rows):
    lines = []
    for h in rows:
        lines.append("".join("#" if h & (1 << (15 - x)) else "." for x in range(15)))
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    for ch in (sys.argv[1] if len(sys.argv) > 1 else "한글"):
        rows = render_glyph(ch)
        print(f"--- {ch!r} ---")
        print(ascii_art(rows))
