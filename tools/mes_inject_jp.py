"""Inject Korean translations into the JAPANESE disc image.

Design (2026-07, JP switch):
- Record skeleton comes from the ENGLISH image (translation JSONs are aligned to its
  ASCII runs, record ids match the JP image 1:1). The rebuilt records + a rebuilt font
  block replace the same-named MES inside the JP image.
- The JP game never uses ASCII from the dialogue font pages (original fills page0
  255/256 + page1 127/128 cells with kanji), so ALL 382 codes are free:
      bank0 byte 0x01..0xFF (255 cells, page0 256x256)
    + bank1 byte 0x01..0x7F (127 cells, page1 256x128)
  metric table 0x180 covers codes 0x000..0x17F. No engine patch.
- Every rendered character (hangul, ASCII, punctuation) goes through the dynamic
  per-file charset; glyphs are AA-rendered. Codes are assigned by frequency so the
  255 most frequent chars sit on bank0 and bank switches stay rare.
- Output = ESMD + records + font block, padded with zeros to the JP file's original
  size (JP files have zero slack: records + 0xC180 exactly). If the rebuild is larger,
  we fail loudly — caller must relocate (img_relocate) instead.

Translation input: {rid: [run0_kr, run1_kr, ...]} — one Korean string per ASCII text
run of the ENGLISH record, in run order. None leaves that run as English.
"""
import struct, sys, os, json, collections
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse, encode
from render_glyph_aa import render_aa
from img_patch import apply as img_apply

IMG_EN = r"D:\Works\tear\티어링사가(eng).img"
IMG_JP_SRC = r"D:\Works\tear\Yutona Eiyuu Senki - TearRingSaga (Japan).bin"  # pristine: skeleton/text source
IMG_JP = r"D:\Works\tear\build\tear_kr_jp.bin"                               # build: patch target

BLOCK_LEN = 0xC180
PAGE1_OFF = 0x8000
METRIC_OFF = 0xC000
SLOTS = [(0, b) for b in range(0x01, 0x100)] + [(1, b) for b in range(0x01, 0x80)]  # 382

_glyph_cache = {}
def glyph16(ch):
    if ch not in _glyph_cache:
        g, w = render_aa(ch, size=14, box=16, dy=1)
        if ch == " ":
            w = 5
        _glyph_cache[ch] = (g, w)
    return _glyph_cache[ch]

def _index(img_path):
    ix.f = open(img_path, "rb")
    return ix.build_index()

def _read(img_path, idx, name):
    ix.f = open(img_path, "rb")
    lba, size, _ = idx[name]
    return ix.read_user(lba, size), lba, size

def _is_ascii_char(t):
    return t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F

def record_chars(toks, tr):
    """Yield the final character stream of one record as ('ch', unicode_char) /
    ('ctrl', tok) items, applying run translations. (EN skeleton: ASCII runs.)"""
    out = []
    run_no = -1
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if _is_ascii_char(t):
            run_no += 1
            j = i
            while j < n and _is_ascii_char(toks[j]):
                j += 1
            kr = None
            if tr and run_no < len(tr):
                kr = tr[run_no]
            if kr is None:
                for k in range(i, j):
                    out.append(("ch", chr(toks[k][2])))
            else:
                for ch in kr:
                    out.append(("ch", ch))
            i = j
        elif t[0] == "char":
            raise ValueError(f"unexpected non-ASCII char token in EN record: {t}")
        else:
            op = t[1]
            if op is not None and (op & 0xF0) == 0x40:
                i += 1
                continue  # drop source bank switches; encode() re-adds ours
            out.append(("ctrl", t))
            i += 1
    return out

def _strip_bank_switches(toks):
    """Bank switches are encoding artifacts, not run boundaries."""
    return [t for t in toks
            if not (t[0] == "ctrl" and t[1] is not None and (t[1] & 0xF0) == 0x40)]

def record_chars_jp(toks, tr, jp_chars):
    """JP-skeleton variant: runs = consecutive char tokens (any bank), decoded via
    jp_chars (code -> unicode). tr[run_no] replaces the run's text; None keeps
    the original Japanese (re-encoded through the dynamic charset)."""
    toks = _strip_bank_switches(toks)
    out = []
    run_no = -1
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t[0] == "char":
            run_no += 1
            j = i
            while j < n and toks[j][0] == "char":
                j += 1
            kr = None
            if tr and run_no < len(tr):
                kr = tr[run_no]
            if kr is None:
                for k in range(i, j):
                    code = (toks[k][1] << 8) | toks[k][2]
                    out.append(("ch", jp_chars.get(code, "?")))
            else:
                for ch in kr:
                    out.append(("ch", ch))
            i = j
        else:
            op = t[1]
            if op is not None and (op & 0xF0) == 0x40:
                i += 1
                continue
            out.append(("ctrl", t))
            i += 1
    return out

def jp_char_table(mes_name):
    """code -> unicode char for one JP MES, via jp_glyphs filemap + glyph map."""
    import os
    TR = r"D:\Works\tear\trdata"
    meta = json.load(open(os.path.join(TR, "jp_glyphs.json"), encoding="utf-8"))
    auto = json.load(open(os.path.join(TR, "jp_glyph_map_auto.json"), encoding="utf-8"))
    chars = [g["char"] for g in auto]
    fixp = os.path.join(TR, "jp_glyph_map_fix.json")
    if os.path.exists(fixp):
        for k, v in json.load(open(fixp, encoding="utf-8")).items():
            if not k.startswith("_"):
                chars[int(k)] = v
    fmap = meta["filemaps"][mes_name]
    return {int(c, 16): (chars[gi] if gi >= 0 else "　") for c, gi in fmap.items()}

def dump_template(mes_name, out_path=None):
    """Write a translation template JSON: JP runs per record, ready to fill with Korean."""
    idx_jp = _index(IMG_JP_SRC)
    d_jp, _, _ = _read(IMG_JP_SRC, idx_jp, mes_name)
    jp = jp_char_table(mes_name)
    recs, _ = parse_records(d_jp)
    tpl = {"_file": mes_name, "_skeleton": "jp"}
    for off, sz, rid, pl in recs:
        toks = _strip_bank_switches(parse(pl))
        runs = []
        cur = []
        for t in toks:
            if t[0] == "char":
                cur.append(jp.get((t[1] << 8) | t[2], "?"))
            elif cur:
                runs.append("".join(cur))
                cur = []
        if cur:
            runs.append("".join(cur))
        if runs:
            tpl[str(rid)] = {"_jp": runs, "kr": [None] * len(runs)}
    if out_path:
        json.dump(tpl, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"template -> {out_path}")
    return tpl

def inject_file(mes_name, translations, verbose=True, skeleton="en"):
    """Rebuild one MES from EN or JP records + translations, sized for the JP image.
    Returns (new_bytes, jp_lba, jp_size, charmap)."""
    idx_src = _index(IMG_JP_SRC)
    d_jp, _, _ = _read(IMG_JP_SRC, idx_src, mes_name)   # pristine JP: skeleton + font base
    idx_jp = _index(IMG_JP)
    _, jp_lba, jp_size = _read(IMG_JP, idx_jp, mes_name)  # build image: patch target/budget
    assert d_jp[:4] == b"ESMD"
    if skeleton == "jp":
        recs_src, _ = parse_records(d_jp)
        jp = jp_char_table(mes_name)
    else:
        idx_en = _index(IMG_EN)
        d_en, _, _ = _read(IMG_EN, idx_en, mes_name)
        assert d_en[:4] == b"ESMD"
        recs_src, _ = parse_records(d_en)

    # pass 1: final char streams per record + global frequency.
    # Records WITHOUT a translation are kept byte-verbatim (None stream): meta
    # records (id 0/9999) may be engine-special, and re-encoding untranslated
    # text would point at reassigned font cells anyway.
    streams = []
    freq = collections.Counter()
    for off, sz, rid, pl in recs_src:
        if translations.get(rid) is None:
            streams.append((rid, None, pl))
            continue
        if skeleton == "jp":
            stream = record_chars_jp(parse(pl), translations.get(rid), jp)
        else:
            stream = record_chars(parse(pl), translations.get(rid))
        streams.append((rid, stream, pl))
        for kind, v in stream:
            if kind == "ch":
                freq[v] += 1
    if len(freq) > len(SLOTS):
        raise RuntimeError(f"{mes_name}: {len(freq)} distinct chars > {len(SLOTS)} slots")

    # pass 2: assign codes by frequency (bank0 first)
    charmap = {}
    for slot, (ch, _) in zip(SLOTS, freq.most_common()):
        charmap[ch] = slot

    # pass 3: encode records (verbatim for untranslated)
    recs_out = []
    for rid, stream, pl in streams:
        if stream is None:
            recs_out.append([rid, bytearray(pl)])
            continue
        toks = []
        for kind, v in stream:
            if kind == "ch":
                bank, byte = charmap[v]
                toks.append(("char", bank, byte))
            else:
                toks.append(v)
        recs_out.append([rid, bytearray(encode(toks))])

    # 4-align the font block by padding INSIDE the last record's payload
    total = 4 + sum(8 + len(p) for _, p in recs_out)
    pad = (4 - total % 4) % 4
    if pad and recs_out:
        recs_out[-1][1] += b"\x00" * pad
    new_records = bytearray()
    for rid, pl in recs_out:
        new_records += struct.pack("<II", len(pl), rid) + bytes(pl)

    # font block: keep JP original as base (glyphs AND metric — the engine may
    # touch fixed codes unconditionally; zeroing them broke scene playback),
    # overwrite only the cells we allocate.
    recs_jp, consumed_jp = parse_records(d_jp)
    fb_jp = (consumed_jp + 3) & ~3
    block = bytearray(d_jp[fb_jp:fb_jp + BLOCK_LEN])
    assert len(block) == BLOCK_LEN, f"{mes_name}: JP font block short ({len(block):#x})"
    for ch, (bank, b) in charmap.items():
        v = b & 0xF0
        u_bytes = (b & 0x0F) * 8
        base = PAGE1_OFF if bank == 1 else 0
        g, width = glyph16(ch)
        for dy in range(16):
            dst = base + (v + dy) * 128 + u_bytes
            block[dst:dst + 8] = g[dy * 8:dy * 8 + 8]
        block[METRIC_OFF + ((bank << 8) | b)] = width

    out = bytearray(b"ESMD")
    out += new_records
    out += block
    if verbose:
        print(f"{mes_name}: chars={len(freq)} (bank0 {min(len(freq),255)}, "
              f"bank1 {max(0,len(freq)-255)}), rebuilt {len(out)}B vs JP {jp_size}B")
    return bytes(out), jp_lba, jp_size, charmap

def apply_json(tr_json_path):
    raw = json.load(open(tr_json_path, encoding="utf-8"))
    if raw.get("_skip"):
        print(f"{raw.get('_file')}: SKIPPED ({raw['_skip'][:40]}...)")
        return None
    mes_name = raw["_file"]
    skeleton = raw.get("_skeleton", "en")
    tr = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        kr = v["kr"] if isinstance(v, dict) else v
        if kr is not None and not any(x is not None for x in kr):
            kr = None  # nothing translated -> keep record byte-verbatim
        tr[int(k)] = kr
    new, jp_lba, jp_size, charmap = inject_file(mes_name, tr, skeleton=skeleton)
    if len(new) <= jp_size:
        new = new + b"\x00" * (jp_size - len(new))
        img_apply(IMG_JP, [(jp_lba, 0, new)])
        print(f"{mes_name}: injected in place into {IMG_JP}")
    else:
        from img_relocate import relocate
        relocate(IMG_JP, mes_name, new)
        print(f"{mes_name}: relocated (+{len(new)-jp_size}B) in {IMG_JP}")
    return charmap

if __name__ == "__main__":
    for p in sys.argv[1:]:
        apply_json(p)
