"""Extract all text records from every dialogue MES, verify lossless round-trip,
and produce a translation corpus + glyph/char statistics.

MES layout (confirmed): ESMD magic (4) then a run of text records
  [u32 size][u32 id][payload(size)]
until a zero/size==0 boundary; the tail holds the embedded font block + zero padding.
Round-trip: record region [4:consumed] rebuilt byte-identical, tail preserved.
"""
import struct, sys, os, json, collections
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix

def parse_records(d):
    """Return (records, consumed). records: list of (offset, size, id, payload)."""
    assert d[:4] == b"ESMD"
    off = 4
    recs = []
    while off + 8 <= len(d):
        size, rid = struct.unpack_from("<II", d, off)
        if size == 0 or off + 8 + size > len(d):
            break
        recs.append((off, size, rid, d[off+8:off+8+size]))
        off += 8 + size
    return recs, off

def rebuild(d, recs, consumed):
    """Reassemble record region from recs; must equal d[4:consumed]."""
    out = bytearray()
    for off, size, rid, pl in recs:
        out += struct.pack("<II", size, rid) + pl
    return bytes(out) == d[4:consumed]

def decode_text(payload):
    """Split payload into readable text + control tokens. Returns list of segments."""
    segs = []
    i = 0
    cur = []
    while i < len(payload):
        b = payload[i]
        if b == 0 and i + 1 < len(payload):
            if cur:
                segs.append(("t", "".join(cur)))
                cur = []
            segs.append(("c", payload[i+1]))
            i += 2
        elif 0x20 <= b < 0x7F:
            cur.append(chr(b))
            i += 1
        else:
            if cur:
                segs.append(("t", "".join(cur)))
                cur = []
            segs.append(("b", b))
            i += 1
    if cur:
        segs.append(("t", "".join(cur)))
    return segs

if __name__ == "__main__":
    ix.f = open(r"D:\Works\tear\티어링사가(eng).img", "rb")
    idx = ix.build_index()
    mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)

    total_recs = 0
    total_chars = 0
    charset = collections.Counter()
    rt_ok = rt_bad = 0
    corpus = {}
    for k in mes:
        lba, size, _ = idx[k]
        d = ix.read_user(lba, size)
        if d[:4] != b"ESMD":
            continue
        recs, consumed = parse_records(d)
        if rebuild(d, recs, consumed):
            rt_ok += 1
        else:
            rt_bad += 1
            print("ROUND-TRIP FAIL:", k)
        entries = []
        for off, sz, rid, pl in recs:
            plain = "".join(seg[1] for seg in decode_text(pl) if seg[0] == "t")
            for ch in plain:
                charset[ch] += 1
            total_chars += len(plain)
            entries.append({"id": rid, "size": sz, "text": plain})
        total_recs += len(recs)
        corpus[k] = entries

    print(f"MES files: {len(corpus)}, records: {total_recs}, round-trip {rt_ok} ok / {rt_bad} bad")
    print(f"total ASCII text chars: {total_chars}")
    print(f"distinct chars: {len(charset)}")
    print("charset:", "".join(sorted(charset)))
    outdir = r"D:\Works\tear\trdata"
    os.makedirs(outdir, exist_ok=True)
    json.dump(corpus, open(os.path.join(outdir, "corpus_en.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", os.path.join(outdir, "corpus_en.json"))
