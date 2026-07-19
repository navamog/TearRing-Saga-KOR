"""Relocate an oversized (expanded-font) MES to the end of the disc image and update
all references: EMBLEM.FAT entry, ISO9660 directory record, PVD volume space.

Raw Mode2/2352 data sector: sync(12) + header(4) + subheader(8) + user(2048) + EDC/ECC.
"""
import struct, sys, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from cd_edcecc import sector_fix
from img_patch import apply as img_apply

SECTOR, USER_OFF, USER_LEN = 2352, 24, 2048

def _bcd(n):
    return ((n // 10) << 4) | (n % 10)

def _write_data_sector(f, lba, data2048):
    raw = bytearray(SECTOR)
    raw[0] = 0
    raw[1:11] = b"\xff" * 10
    raw[11] = 0
    a = lba + 150
    raw[12] = _bcd(a // 4500)
    raw[13] = _bcd((a // 75) % 60)
    raw[14] = _bcd(a % 75)
    raw[15] = 2  # mode 2
    raw[16:24] = bytes([0, 0, 0x08, 0, 0, 0, 0x08, 0])  # subheader: Form1 data
    raw[24:24 + USER_LEN] = data2048.ljust(USER_LEN, b"\x00")
    sector_fix(raw)
    f.seek(lba * SECTOR)
    f.write(raw)

def _find_fat_entry(img, name):
    """Return (fat_lba, byte_offset_in_fat) of the EMBLEM.FAT 24B entry for `name`."""
    ix.f = open(img, "rb")
    idx = ix.build_index()
    flba, fsize, _ = idx["/EMBLEM.FAT"]
    fat = ix.read_user(flba, fsize)
    nb = name.encode()
    for i in range(len(fat) // 24):
        e = fat[i*24:(i+1)*24]
        if e[1:16].split(b"\x00")[0] == nb:
            return flba, i * 24
    raise KeyError(f"{name} not in EMBLEM.FAT")

def _find_dir_record(img, dir_path, name):
    """Return (dir_lba, byte_offset) of the ISO9660 record for `name` (with ;1) in dir_path."""
    ix.f = open(img, "rb")
    idx = ix.build_index()
    dlba, dsize, _ = idx[dir_path]
    data = ix.read_user(dlba, dsize)
    want = (name + ";1").encode()
    off = 0
    while off < dsize:
        ln = data[off]
        if ln == 0:
            off = (off // 2048 + 1) * 2048
            continue
        nl = data[off + 32]
        rec_name = data[off + 33:off + 33 + nl]
        if rec_name == want:
            return dlba, off
        off += ln
    raise KeyError(f"{name} not in {dir_path}")

def relocate(img, iso_path, new_data):
    """iso_path e.g. '/MG1/GEVMSG08.MES'. Writes new_data at image end and fixes references."""
    dir_path, fname = iso_path.rsplit("/", 1)
    dir_path = dir_path or "/"
    # 1. append sectors at image end
    f = open(img, "r+b")
    f.seek(0, 2)
    total = f.tell() // SECTOR
    new_lba = total
    n = (len(new_data) + USER_LEN - 1) // USER_LEN
    for i in range(n):
        _write_data_sector(f, new_lba + i, new_data[i*USER_LEN:(i+1)*USER_LEN])
    f.close()
    new_total = new_lba + n

    patches = []
    # 2. EMBLEM.FAT: entry LBA (off+16) + size (off+20), both u32 LE
    flba, foff = _find_fat_entry(img, fname)
    patches.append((flba, foff + 16, struct.pack("<I", new_lba)))
    patches.append((flba, foff + 20, struct.pack("<I", len(new_data))))
    # 3. ISO dir record: LBA (off+2 LE, off+6 BE), size (off+10 LE, off+14 BE)
    dlba, roff = _find_dir_record(img, dir_path, fname)
    patches.append((dlba, roff + 2, struct.pack("<I", new_lba)))
    patches.append((dlba, roff + 6, struct.pack(">I", new_lba)))
    patches.append((dlba, roff + 10, struct.pack("<I", len(new_data))))
    patches.append((dlba, roff + 14, struct.pack(">I", len(new_data))))
    # 4. PVD volume space (LBA16 user off 80 LE, off 84 BE)
    patches.append((16, 80, struct.pack("<I", new_total)))
    patches.append((16, 84, struct.pack(">I", new_total)))
    img_apply(img, patches)
    print(f"relocated {iso_path} -> LBA {new_lba} ({n} sec, {len(new_data)}B), image now {new_total} sec")
    return new_lba
