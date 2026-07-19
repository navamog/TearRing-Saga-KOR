"""Exact parser/encoder for MES dialogue payloads (matches engine parser 0x80067AA8).

Token stream:
  ('char', bank, byte)         one rendered glyph, code = (bank<<8)|byte
  ('ctrl', opcode, params)     control code 0x00XX with its parameter bytes
Bank is set by opcode 0x4X (low nibble = bank). 'char' bytes are nonzero.

Control parameter lengths (disassembled):
  0x00 end | 0x10,0x20,0x40,0x60,0x70,0x80 -> 0 | 0x30 -> 3 | 0x50 -> 1+next_byte
"""

def parse(pl):
    toks = []
    i = 0
    bank = 0
    n = len(pl)
    while i < n:
        b = pl[i]
        if b != 0:
            toks.append(("char", bank, b))
            i += 1
            continue
        # b == 0 -> control
        if i + 1 >= n:
            toks.append(("ctrl", None, b""))  # trailing lone 0
            i += 1
            break
        op = pl[i + 1]
        hi = op & 0xF0
        i += 2
        if hi == 0x00:
            toks.append(("ctrl", op, b""))
            if op == 0x00:
                # end marker; but payload may continue with more records' text? keep parsing
                pass
            continue
        if hi == 0x40:
            bank = (op & 0x0F)
            toks.append(("ctrl", op, b""))
            continue
        if hi == 0x30:
            params = pl[i:i+3]; i += 3
        elif hi == 0x50:
            s0 = pl[i]; params = pl[i:i+1+s0]; i += 1 + s0
        else:  # 0x10,0x20,0x60,0x70,0x80
            params = b""
        toks.append(("ctrl", op, params))
    return toks

def encode(toks):
    out = bytearray()
    bank = 0
    for t in toks:
        if t[0] == "char":
            tbank, b = t[1], t[2]
            if tbank != bank:
                out += bytes([0x00, 0x40 | (tbank & 0x0F)])
                bank = tbank
            out += bytes([b])
        else:  # ctrl
            op, params = t[1], t[2]
            if op is None:
                out += b"\x00"
            else:
                out += bytes([0x00, op]) + params
                if (op & 0xF0) == 0x40:
                    bank = op & 0x0F
    return bytes(out)

def text_of(toks):
    """Concatenate rendered chars (bank0 ASCII shown as-is)."""
    return "".join(chr(t[2]) if t[1] == 0 and 0x20 <= t[2] < 0x7F else f"\\x{t[2]:02x}" for t in toks if t[0] == "char")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, r"D:\Works\tear\tools")
    import iso_extract as ix
    from mes_extract import parse_records
    ix.f = open(r"D:\Works\tear\티어링사가(eng).img", "rb")
    idx = ix.build_index()
    mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)
    ok = bad = 0
    bad_files = []
    for k in mes:
        d = ix.read_user(*idx[k][:2])
        if d[:4] != b"ESMD":
            continue
        recs, _ = parse_records(d)
        for off, sz, rid, pl in recs:
            toks = parse(pl)
            if encode(toks) == pl:
                ok += 1
            else:
                bad += 1
                if k not in bad_files:
                    bad_files.append(k)
    print(f"payload round-trip: {ok} ok, {bad} bad")
    if bad_files:
        print("bad files:", bad_files[:10])
        # show first mismatch
        d = ix.read_user(*idx[bad_files[0]][:2])
        recs, _ = parse_records(d)
        for off, sz, rid, pl in recs:
            if encode(parse(pl)) != pl:
                e = encode(parse(pl))
                for j in range(min(len(e), len(pl))):
                    if e[j] != pl[j]:
                        print(f"  {bad_files[0]} id={rid} mismatch at {j}: orig {pl[max(0,j-6):j+6].hex(' ')} got {e[max(0,j-6):j+6].hex(' ')}")
                        break
                break
