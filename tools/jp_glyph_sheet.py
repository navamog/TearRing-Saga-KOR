"""Render verification sheets: game glyph (4x) + auto-matched char render + label.
Usage: jp_glyph_sheet.py <start> <end> [out.png]  (glyph indices by frequency rank)
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageFont, ImageDraw

TR = r"D:\Works\tear\trdata"

def game_glyph_img(raw, i, scale=4):
    cellb = raw[i*128:(i+1)*128]
    img = Image.new("L", (16, 16), 0)
    px = img.load()
    for j, b in enumerate(cellb):
        for k, nib in enumerate((b & 0xF, b >> 4)):
            v = 0 if nib == 0 else int((16 - nib) / 15 * 255)
            px[(j % 8) * 2 + k, j // 8] = v
    return img.resize((16*scale, 16*scale), Image.NEAREST)

if __name__ == "__main__":
    start, end = int(sys.argv[1]), int(sys.argv[2])
    out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(TR, f"sheet_{start}_{end}.png")
    raw = open(os.path.join(TR, "jp_glyphs.bin"), "rb").read()
    amap = json.load(open(os.path.join(TR, "jp_glyph_map_auto.json"), encoding="utf-8"))
    order = sorted(range(len(amap)), key=lambda i: -amap[i]["count"])
    sel = order[start:end]

    scale = 4
    cell_w, cell_h = 64 + 64 + 40, 72   # game | render | text
    cols = 8
    rows = (len(sel) + cols - 1) // cols
    sheet = Image.new("L", (cols * cell_w, rows * cell_h), 255)
    label_font = ImageFont.truetype(r"C:\Windows\Fonts\msgothic.ttc", 16)
    big_font = ImageFont.truetype(r"C:\Windows\Fonts\msgothic.ttc", 60)
    d = ImageDraw.Draw(sheet)
    for n, gi in enumerate(sel):
        x0, y0 = (n % cols) * cell_w, (n // cols) * cell_h
        g = game_glyph_img(raw, gi, scale)
        inv = Image.eval(g, lambda v: 255 - v)
        sheet.paste(inv, (x0, y0))
        ch = amap[gi]["char"]
        d.text((x0 + 66, y0 - 2), ch, fill=0, font=big_font)
        d.text((x0 + 132, y0 + 8), f"#{gi}", fill=0, font=label_font)
        d.text((x0 + 132, y0 + 28), f"{amap[gi]['score']:.2f}", fill=0, font=label_font)
    sheet.save(out_path)
    print("wrote", out_path, sheet.size)
