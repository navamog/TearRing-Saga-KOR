"""CD-ROM XA Mode2 Form1/Form2 EDC/ECC computation (classic ECM-style algorithm).

Raw 2352-byte sector layout (Mode2 Form1):
  [0:12] sync | [12:16] header | [16:24] subheader | [24:2072] data(2048)
  [2072:2076] EDC over [16:2072]
  [2076:2248] ECC-P (172B) | [2248:2352] ECC-Q (104B)
  ECC covers [12:2076] with header zeroed (XA).
Form2: [24:2348] data(2324), [2348:2352] EDC over [16:2348], no ECC.
"""
import struct

EDC_LUT = []
for _i in range(256):
    _e = _i
    for _ in range(8):
        _e = (_e >> 1) ^ (0xD8018001 if _e & 1 else 0)
    EDC_LUT.append(_e)

ECC_F = [0] * 256
ECC_B = [0] * 256
for _i in range(256):
    _j = ((_i << 1) ^ (0x11D if _i & 0x80 else 0)) & 0xFF
    ECC_F[_i] = _j
    ECC_B[_i ^ _j] = _i

def edc_compute(data):
    edc = 0
    for b in data:
        edc = EDC_LUT[(edc ^ b) & 0xFF] ^ (edc >> 8)
    return edc

def _ecc_block(src, major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    dest = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        ecc_a = 0
        ecc_b = 0
        for _ in range(minor_count):
            temp = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            ecc_a ^= temp
            ecc_b ^= temp
            ecc_a = ECC_F[ecc_a]
        ecc_a = ECC_B[ECC_F[ecc_a] ^ ecc_b]
        dest[major] = ecc_a
        dest[major + major_count] = ecc_a ^ ecc_b
    return dest

def sector_fix(raw):
    """raw: 2352-byte bytearray, Mode2 sector. Recomputes EDC (+ECC for Form1) in place."""
    assert len(raw) == 2352
    form2 = raw[18] & 0x20
    if form2:
        struct.pack_into("<I", raw, 2348, edc_compute(raw[16:2348]))
        return raw
    struct.pack_into("<I", raw, 2072, edc_compute(raw[16:2072]))
    body = bytearray(raw[12:2352])  # working copy from header
    body[0:4] = b"\x00\x00\x00\x00"  # XA: zero address for ECC
    p = _ecc_block(body, 86, 24, 2, 86)
    body[2064:2236] = p
    q = _ecc_block(body, 52, 43, 86, 88)
    raw[2076:2248] = p
    raw[2248:2352] = q
    return raw

def verify_image_sectors(img_path, lba_list):
    """Self-test: recompute EDC/ECC on given sectors and compare with stored bytes."""
    ok = bad = 0
    with open(img_path, "rb") as f:
        for lba in lba_list:
            f.seek(lba * 2352)
            raw = bytearray(f.read(2352))
            orig = bytes(raw)
            sector_fix(raw)
            if bytes(raw) == orig:
                ok += 1
            else:
                bad += 1
                d = [i for i in range(2352) if raw[i] != orig[i]]
                print(f"LBA {lba}: MISMATCH at {len(d)} bytes, first at {d[0]} (region {'EDC' if 2072<=d[0]<2076 else 'P' if 2076<=d[0]<2248 else 'Q' if d[0]>=2248 else 'data?'})")
    print(f"verify: {ok} ok, {bad} mismatch")
    return bad == 0

if __name__ == "__main__":
    import sys, random
    img = sys.argv[1]
    random.seed(1)
    lbas = [random.randrange(23, 252000) for _ in range(50)]
    verify_image_sectors(img, lbas)
