"""Inject Korean translations into a MES file: rebuild text records with hangul
(bank1 encoding), fill page1 glyph sheet + metric widths, keep file size == original,
and write in place to the disc image (EDC/ECC recalculated).

Translation input: {rid: [run0_kr, run1_kr, ...]} — one Korean string per ASCII text run,
in run order. A None entry leaves that run as original English.
"""
import struct, sys, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse, encode
from render_glyph_aa import render_aa
from img_patch import apply as img_apply

IMG = r"D:\Works\tear\build\tear_kr_test.img"
HANGUL0 = 0xAC00
HANGUL1 = 0xD7A3

def is_hangul(ch):
    return HANGUL0 <= ord(ch) <= HANGUL1

def find_font_block(d):
    """Return (block_start, ascii_glyph_off). Font block = ascii_glyph - 0x1000."""
    # ascii glyph sub-block: locate via a known ASCII 'A' row is fragile; instead
    # font block is right after last text record. Use parse_records consumed as block start.
    recs, consumed = parse_records(d)
    return consumed, consumed + 0x1000  # block start, ascii glyph area

_glyph_cache = {}
def glyph16(ch):
    """Return (128-byte 4bpp cell, advance_width). AA rendered."""
    if ch not in _glyph_cache:
        g, w = render_aa(ch, size=14, box=16, dy=1)
        if ch == " ":
            w = 5  # half-width space (full glyph is blank; just narrow the advance)
        _glyph_cache[ch] = (g, w)
    return _glyph_cache[ch]

def extract_runs(toks):
    runs = []
    cur = []
    for t in toks:
        if t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F:
            cur.append(t)
        else:
            if cur:
                runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return runs

def inject(d, translations, syllable_map):
    """Return new MES bytes (same length as d). syllable_map: dict ch->byte, updated in place."""
    recs, consumed = parse_records(d)
    orig_len = len(d)
    block_start = consumed
    block = bytearray(d[block_start:block_start + 0xC180])  # ORIGINAL block, no engine patch
    page1_data = 0x8000
    metric_off = 0xC000

    # 224 hangul slots WITHOUT engine patch, using VRAM-safe areas only:
    #   bank1 page1 byte 0x21..0x7F (rows 2..7, 95)  +  bank0 page0 byte 0x80..0xFF (rows 8..15, 128)
    # page0 is already uploaded at h=256 by the game, so rows 8..15 are font-owned VRAM (safe).
    slots = [(1, b) for b in range(0x21, 0x80)] + [(0, b) for b in range(0x80, 0x100)]
    slot_idx = [0]
    def code_for(ch):
        if ch in syllable_map:
            return syllable_map[ch]
        if slot_idx[0] >= len(slots):
            raise RuntimeError(f"font full: >{len(slots)} syllables in one file")
        bb = slots[slot_idx[0]]
        slot_idx[0] += 1
        syllable_map[ch] = bb
        return bb

    # rebuild records
    recs_out = []
    for off, sz, rid, pl in recs:
        toks = parse(pl)
        tr = translations.get(rid)
        if tr is None:
            new_pl = pl
        else:
            runs = extract_runs(toks)
            # map each run (by identity) to its translation
            run_ids = {id(r[0]): i for i, r in enumerate(runs)}
            new_toks = []
            i = 0
            while i < len(toks):
                t = toks[i]
                if t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F:
                    # start of a run
                    ri = None
                    for idx, r in enumerate(runs):
                        if r[0] is t:
                            ri = idx; break
                    # advance past run
                    j = i
                    while j < len(toks) and toks[j][0] == "char" and toks[j][1] == 0 and 0x20 <= toks[j][2] < 0x7F:
                        j += 1
                    kr = tr[ri] if (ri is not None and ri < len(tr) and tr[ri] is not None) else None
                    if kr is None:
                        new_toks.extend(toks[i:j])
                    else:
                        for ch in kr:
                            bank, byte = code_for(ch)
                            new_toks.append(("char", bank, byte))
                    i = j
                else:
                    new_toks.append(t); i += 1
            new_pl = encode(new_toks)
        recs_out.append([rid, bytearray(new_pl)])

    # pad last record's payload so the font block (right after records) is 4-aligned.
    # The engine locates the font block at the record-walk end, so padding must live
    # INSIDE the last record (counted in its size), not between records.
    total = 4 + sum(8 + len(p) for _, p in recs_out)
    pad = (4 - total % 4) % 4
    if pad and recs_out:
        recs_out[-1][1] += b"\x00" * pad  # trailing 0x00 = end opcodes, harmless
    new_records = bytearray()
    for rid, pl in recs_out:
        new_records += struct.pack("<II", len(pl), rid) + bytes(pl)

    # write glyphs. bank1 -> page1 (block+page1_data), bank0 -> page0 (block+0, upper rows).
    # renderer texcoord: u=(byte&0xF)*16px, v=(byte>>4)*16; advance = metric[bank<<8|byte]
    for ch, (bank, b) in syllable_map.items():
        v = (b & 0xF0)
        u_bytes = (b & 0x0F) * 8
        base = page1_data if bank == 1 else 0
        g, width = glyph16(ch)
        for dy in range(16):
            dst = base + (v + dy) * 128 + u_bytes
            block[dst:dst+8] = g[dy*8:dy*8+8]
        block[metric_off + ((bank << 8) | b)] = width

    # assemble: ESMD + records + block. Original-size font block, so this usually fits the
    # original file (hangul is shorter than English); pad to orig_len if it fits, else caller relocates.
    out = bytearray(b"ESMD")
    out += new_records
    out += block
    if len(out) <= orig_len:
        out += b"\x00" * (orig_len - len(out))
    return bytes(out)

if __name__ == "__main__":
    # sample: translate opening ship dialogue in GEVMSG08.MES
    ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")
    idx = ix.build_index()
    lba, size, _ = idx["/MG1/GEVMSG08.MES"]
    d = ix.read_user(lba, size)

    tr = {26: [
        "루난,", " 거기 있었구나.", "무슨 일이야?", "좀 넋이 나가 보이는데.",
        "오, ", " 홈즈…", "아무것도 아니야.", "그냥 바람 좀 쐬고 있었어.",
        "그렇다면야.", "어쨌든,", " 이제 곧 웰트에 도착해.",
        "너와 네 기사들은 갈 준비가 됐나?",
    ]}
    smap = {}
    new = inject(d, tr, smap)
    print(f"syllables used: {len(smap)}, new size {len(new)} == orig {size}: {len(new)==size}")
    # write in place
    patches = [(lba, 0, new)]
    img_apply(r"D:\Works\tear\build\tear_kr_test.img", patches)
    print("injected GEVMSG08.MES into image")


def apply_json(mes_path_in_img, tr_json_path, img=IMG):
    """Load a translation JSON {rid: [run0, run1, ...]} and inject into one MES in the image."""
    import json as _json
    ix.f = open(img, "rb")
    idx = ix.build_index()
    lba, size, _ = idx[mes_path_in_img]
    d = ix.read_user(lba, size)
    tr_raw = _json.load(open(tr_json_path, encoding="utf-8"))
    tr = {int(k): v for k, v in tr_raw.items() if not k.startswith("_")}
    smap = {}
    new = inject(d, tr, smap)
    img_apply(img, [(lba, 0, new)])
    print(f"{mes_path_in_img}: injected, {len(smap)} syllables, size {len(new)}=={size}")
    return smap
