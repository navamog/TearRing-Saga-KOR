"""Build the KR patch onto build/tear_kr_test.img:
1. engine patches (EXE): page1 h=256, metric table 0x200
2. inject translated MES files (expanded 352-slot font)
3. relocate oversized MES to disc end (EMBLEM.FAT + ISO dir + PVD updated)
"""
import struct, sys, json, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
import mes_inject, img_relocate
from img_patch import apply as img_apply

IMG = r"D:\Works\tear\build\tear_kr_test.img"
EXE_LBA = 746

ENGINE_PATCHES = [
    (0x5B380, 0x24020100),  # page1 rect height 0x80 -> 0x100 (128->256)
    (0x5B394, 0x26108000),  # metric source offset s0 += 0x4000 -> 0x8000
    (0x5B3A4, 0x24040200),  # alloc size 0x180 -> 0x200
    (0x5B3B8, 0x24060200),  # memcpy size 0x180 -> 0x200
]

def patch_engine():
    ps = [(EXE_LBA, off, struct.pack("<I", val)) for off, val in ENGINE_PATCHES]
    img_apply(IMG, ps)
    print("engine patched: page1 h=256, metric 0x200")

def inject_file(iso_path, tr_json=None, verbose=True):
    ix.f = open(IMG, "rb")
    idx = ix.build_index()
    lba, size, _ = idx[iso_path]
    d = ix.read_user(lba, size)
    if d[:4] != b"ESMD":
        return 0
    from mes_extract import parse_records
    recs, consumed = parse_records(d)
    # need a font block (page0+page1+metric) to expand; skip files without one
    if consumed + 0xC180 > size:
        return -1
    tr = {}
    if tr_json:
        tr_raw = json.load(open(tr_json, encoding="utf-8"))
        tr = {int(k): v for k, v in tr_raw.items() if not k.startswith("_")}
    smap = {}
    new = mes_inject.inject(d, tr, smap)
    if len(new) <= size:
        img_apply(IMG, [(lba, 0, new.ljust(size, b"\x00"))])
    else:
        img_relocate.relocate(IMG, iso_path, new)
    if verbose:
        print(f"{iso_path}: {len(smap)} syll, {size}->{len(new)}")
    return len(smap)

TR_FILES = {
    "/MG1/GEVMSG08.MES": r"D:\Works\tear\trdata\ft2-win-data\GEVMSG08_kr.json",
}

if __name__ == "__main__":
    patch_engine()
    ix.f = open(IMG, "rb")
    idx = ix.build_index()
    all_mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)
    ok = skip = 0
    for p in all_mes:
        r = inject_file(p, TR_FILES.get(p), verbose=(p in TR_FILES))
        if r < 0:
            skip += 1
        else:
            ok += 1
    print(f"expanded {ok} MES ({skip} skipped: no font block)")
