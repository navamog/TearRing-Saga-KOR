"""Generate translation templates for the EN-skeleton workflow.

Per MES file, per record: EN text runs (the alignment target for kr),
the decoded Japanese text of the same record (reference), and speaker ctrl ids.

Usage: tr_template.py /MB1/MB0.MES [outpath]
Output JSON:
{ "_file": ..., "_skeleton": "en",
  "<rid>": { "_en": [run, ...], "_jp": "...", "_spk": [ids], "kr": [null, ...] } }
"""
import sys, os, json
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse

IMG_EN = r"D:\Works\tear\티어링사가(eng).img"
TR = r"D:\Works\tear\trdata"

def en_runs(pl):
    runs, cur, spk = [], [], []
    for t in parse(pl):
        if t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F:
            cur.append(chr(t[2]))
        else:
            if cur:
                runs.append("".join(cur)); cur = []
            if t[0] == "ctrl" and t[1] == 0x50 and len(t[2]) >= 3:
                spk.append(int.from_bytes(t[2][1:3], "little"))
    if cur:
        runs.append("".join(cur))
    return runs, spk

def make(mes_name, out_path=None):
    ix.f = open(IMG_EN, "rb")
    idx = ix.build_index()
    d = ix.read_user(*idx[mes_name][:2])
    recs, _ = parse_records(d)
    jp = {}
    cj = json.load(open(os.path.join(TR, "corpus_jp.json"), encoding="utf-8"))
    for e in cj.get(mes_name, []):
        jp[e["id"]] = e["text"]
    tpl = {"_file": mes_name, "_skeleton": "en"}
    for off, sz, rid, pl in recs:
        runs, spk = en_runs(pl)
        if not runs:
            continue
        tpl[str(rid)] = {
            "_en": runs,
            "_jp": jp.get(rid, ""),
            "_spk": sorted(set(spk)),
            "kr": [None] * len(runs),
        }
    if out_path:
        json.dump(tpl, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n = sum(1 for k in tpl if not k.startswith("_"))
        print(f"{mes_name}: {n} text records -> {out_path}")
    return tpl

if __name__ == "__main__":
    name = sys.argv[1]
    # tolerate MSYS path mangling and missing leading slash
    if "/" in name:
        name = "/" + "/".join(p for p in name.split("/") if p)[-0:] if False else name
    up = name.upper()
    for tag in ("MB1/", "MG1/"):
        if tag in up:
            name = "/" + up[up.index(tag):]
            break
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        TR, "tr", name.strip("/").replace("/", "_").replace(".MES", "") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    make(name, out)
