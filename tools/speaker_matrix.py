"""Build a speaker matrix: for every dialogue line, attach the active 0x50 speaker ID.
Output per-speaker line counts + sample lines to identify characters."""
import sys, struct, collections, json
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from mes_extract import parse_records
from mes_codec import parse

ix.f = open(r"D:\Works\tear\티어링사가(eng).img", "rb")
idx = ix.build_index()
mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)

by_speaker = collections.defaultdict(list)  # speaker_id -> list of (file, rid, text)
line_count = collections.Counter()
for k in mes:
    d = ix.read_user(*idx[k][:2])
    if d[:4] != b"ESMD":
        continue
    recs, _ = parse_records(d)
    for off, sz, rid, pl in recs:
        toks = parse(pl)
        speaker = None
        run = []
        for t in toks:
            if t[0] == "ctrl" and t[1] == 0x50 and len(t[2]) >= 3:
                # param 02 lo hi -> id = lo|hi<<8
                speaker = struct.unpack_from("<H", t[2], 1)[0]
            elif t[0] == "char" and t[1] == 0 and 0x20 <= t[2] < 0x7F:
                run.append(chr(t[2]))
            else:
                if run:
                    line_count[speaker] += 1
                    if len(by_speaker[speaker]) < 4:
                        by_speaker[speaker].append("".join(run))
                    run = []
        if run:
            line_count[speaker] += 1
            if len(by_speaker[speaker]) < 4:
                by_speaker[speaker].append("".join(run))

print(f"distinct speaker IDs: {len(line_count)}")
print("top speakers by line count:")
for sid, n in line_count.most_common(40):
    label = f"0x{sid:04X}" if sid is not None else "None"
    samples = " | ".join(by_speaker[sid][:2])[:90]
    print(f"  {label}: {n:5d} lines   e.g. {samples}")
