"""Collect every glyph cell used by text in every JP MES, cluster identical bitmaps
globally, and dump usage stats. Output: trdata/jp_glyphs.json
  { "glyphs": [ {"hash": h, "count": n, "files": k, "width": w} ... ],   # by first-seen order
    "filemaps": { mes_name: { "code:XXX": glyph_index } } }
plus raw bitmaps in trdata/jp_glyphs.bin (128B each, same order).
"""
import struct, sys, os, json, collections, hashlib
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse

IMG_JP = r"D:\Works\tear\Yutona Eiyuu Senki - TearRingSaga (Japan).bin"
BLOCK_LEN = 0xC180

def cell(block, code):
    page_off = 0 if code < 0x100 else 0x8000
    i = code & 0xFF if code < 0x100 else code - 0x100
    r, c = i // 16, i % 16
    out = bytearray()
    for row in range(16):
        out += block[page_off + (r*16+row)*128 + c*8 : page_off + (r*16+row)*128 + c*8 + 8]
    return bytes(out)

if __name__ == "__main__":
    ix.f = open(IMG_JP, "rb")
    idx = ix.build_index()
    mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)

    glyph_index = {}      # bitmap -> global index
    glyphs = []           # [ [bitmap, count, fileset, width] ]
    filemaps = {}
    for name in mes:
        d = ix.read_user(*idx[name][:2])
        if d[:4] != b"ESMD":
            continue
        recs, consumed = parse_records(d)
        fb = (consumed + 3) & ~3
        block = d[fb:fb + BLOCK_LEN]
        if len(block) < BLOCK_LEN:
            print(f"{name}: short font block, skip")
            continue
        # codes actually referenced by text
        used = collections.Counter()
        for off, sz, rid, pl in recs:
            for t in parse(pl):
                if t[0] == "char":
                    used[(t[1] << 8) | t[2]] += 1
        fmap = {}
        for code, cnt in used.items():
            bm = cell(block, code)
            if not any(bm):
                fmap[f"{code:#x}"] = -1  # blank glyph (space?)
                continue
            gi = glyph_index.get(bm)
            if gi is None:
                gi = len(glyphs)
                glyph_index[bm] = gi
                w = block[0xC000 + code] if code < 0x180 else 0
                glyphs.append([bm, 0, set(), w])
            glyphs[gi][1] += cnt
            glyphs[gi][2].add(name)
            fmap[f"{code:#x}"] = gi
        filemaps[name] = fmap

    print(f"files: {len(filemaps)}, unique glyph bitmaps: {len(glyphs)}")
    top = sorted(range(len(glyphs)), key=lambda i: -glyphs[i][1])[:10]
    for i in top:
        print(f"  glyph {i}: count={glyphs[i][1]} files={len(glyphs[i][2])} w={glyphs[i][3]}")

    os.makedirs(r"D:\Works\tear\trdata", exist_ok=True)
    with open(r"D:\Works\tear\trdata\jp_glyphs.bin", "wb") as f:
        for bm, cnt, files, w in glyphs:
            f.write(bm)
    meta = {
        "glyphs": [{"count": cnt, "files": len(files), "width": w}
                   for bm, cnt, files, w in glyphs],
        "filemaps": filemaps,
    }
    json.dump(meta, open(r"D:\Works\tear\trdata\jp_glyphs.json", "w", encoding="utf-8"))
    print("wrote trdata/jp_glyphs.bin + jp_glyphs.json")
