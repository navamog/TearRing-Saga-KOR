"""Decode all JP MES text into a readable Japanese corpus using the glyph->char map.

Inputs:  trdata/jp_glyphs.json (filemaps: mes -> {code: glyph_idx}),
         trdata/jp_glyph_map_auto.json (auto guesses),
         trdata/jp_glyph_map_fix.json (manual corrections {idx: char}, optional)
Output:  trdata/corpus_jp.json  { mes: [ {"id": rid, "text": "..."} ... ] }
         Markers: newline (00 10) -> "\n", box break (00 70) -> "\n\n".
Unknown/blank glyphs decode to "　"; unresolved indices to "?".
"""
import sys, os, json
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse

IMG_JP = r"D:\Works\tear\Yutona Eiyuu Senki - TearRingSaga (Japan).bin"
TR = r"D:\Works\tear\trdata"

def load_map():
    auto = json.load(open(os.path.join(TR, "jp_glyph_map_auto.json"), encoding="utf-8"))
    chars = [g["char"] for g in auto]
    fixp = os.path.join(TR, "jp_glyph_map_fix.json")
    if os.path.exists(fixp):
        fixes = json.load(open(fixp, encoding="utf-8"))
        for k, v in fixes.items():
            if not k.startswith("_"):
                chars[int(k)] = v
    return chars

def decode_all():
    meta = json.load(open(os.path.join(TR, "jp_glyphs.json"), encoding="utf-8"))
    filemaps = meta["filemaps"]
    chars = load_map()

    ix.f = open(IMG_JP, "rb")
    idx = ix.build_index()
    corpus = {}
    for name, fmap in sorted(filemaps.items()):
        d = ix.read_user(*idx[name][:2])
        recs, _ = parse_records(d)
        entries = []
        for off, sz, rid, pl in recs:
            out = []
            for t in parse(pl):
                if t[0] == "char":
                    code = (t[1] << 8) | t[2]
                    gi = fmap.get(f"{code:#x}", None)
                    if gi is None:
                        out.append("?")
                    elif gi == -1:
                        out.append("　")
                    else:
                        out.append(chars[gi])
                else:
                    op = t[1]
                    if op == 0x10:
                        out.append("\n")
                    elif op == 0x70:
                        out.append("\n\n")
            text = "".join(out).strip("\n")
            entries.append({"id": rid, "text": text})
        corpus[name] = entries
    return corpus

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    corpus = decode_all()
    nrec = sum(len(v) for v in corpus.values())
    nchar = sum(len(e["text"]) for v in corpus.values() for e in v)
    print(f"files={len(corpus)} records={nrec} chars={nchar}")
    json.dump(corpus, open(os.path.join(TR, "corpus_jp.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("wrote trdata/corpus_jp.json")
    # sample
    for e in corpus.get("/MG1/GEVMSG08.MES", [])[:5]:
        if e["text"]:
            print(f"--- rec {e['id']} ---")
            print(e["text"][:300])
