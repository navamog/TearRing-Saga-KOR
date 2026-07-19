"""Build translation working data:
- speaker_lines.json: {speaker_hex: [ {file, rid, run_idx, en} ]}
- glossary_candidates.txt: capitalized proper-noun tokens by frequency (for term unification)
Ordered by story sequence (file name order)."""
import sys, struct, collections, json, re, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse

ix.f = open(r"D:\Works\tear\티어링사가(eng).img", "rb")
idx = ix.build_index()
mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)

speaker_lines = collections.defaultdict(list)
proper = collections.Counter()
total_lines = 0
for k in mes:
    d = ix.read_user(*idx[k][:2])
    if d[:4] != b"ESMD":
        continue
    recs, _ = parse_records(d)
    for off, sz, rid, pl in recs:
        toks = parse(pl)
        speaker = None
        run = []
        run_idx = 0
        def emit():
            global total_lines
            text = "".join(run)
            key = f"{speaker:04X}" if speaker is not None else "NONE"
            speaker_lines[key].append({"file": k, "rid": rid, "run": run_idx, "en": text})
            total_lines += 1
            for m in re.findall(r"[A-Z][a-zA-Z]{2,}", text):
                proper[m] += 1
        for t in toks:
            if t[0] == "ctrl" and t[1] == 0x50 and len(t[2]) >= 3:
                speaker = struct.unpack_from("<H", t[2], 1)[0]
            elif t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F:
                run.append(chr(t[2]))
            else:
                if run:
                    emit(); run = []; run_idx += 1
        if run:
            emit()

out = r"D:\Works\tear\trdata"
os.makedirs(out, exist_ok=True)
json.dump(speaker_lines, open(os.path.join(out, "speaker_lines.json"), "w", encoding="utf-8"), ensure_ascii=False)
# glossary: drop common English words
common = set("The That This With Have What Your You Are And But For Not All His Her She They Them Him Was Who Why How Now Just Its Our Been Will Can Get Got Out Off One Two Yes Sir Lord Lady Well Even More Over Here There Then When Where Come Take Make Look Know Like Only Some Such Very Much Many Long Good Bad".split())
with open(os.path.join(out, "glossary_candidates.txt"), "w", encoding="utf-8") as f:
    for w, n in proper.most_common():
        if w not in common and n >= 5:
            f.write(f"{n:5d}  {w}\n")
print(f"total lines: {total_lines}, speakers: {len(speaker_lines)}")
print(f"glossary candidates: {sum(1 for w,n in proper.items() if w not in common and n>=5)}")
print("wrote trdata/speaker_lines.json, trdata/glossary_candidates.txt")
