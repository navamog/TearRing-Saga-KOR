"""Initial survey of a raw Mode2/2352 PS1 disc image: PVD, root dir listing, SYSTEM.CNF."""
import struct, sys

IMG = sys.argv[1] if len(sys.argv) > 1 else r"D:\Works\tear\티어링사가(eng).img"
SECTOR = 2352
USER_OFF = 24  # Mode2 Form1 user data offset within raw sector
USER_LEN = 2048

f = open(IMG, "rb")

def read_user(lba, count=1):
    out = bytearray()
    for i in range(count):
        f.seek((lba + i) * SECTOR)
        raw = f.read(SECTOR)
        out += raw[USER_OFF:USER_OFF + USER_LEN]
    return bytes(out)

import os
size = os.path.getsize(IMG)
print(f"image size: {size} bytes, sectors: {size / SECTOR}")

# sync check on sector 0
f.seek(0)
raw0 = f.read(32)
print("sector0 head:", raw0[:16].hex())

pvd = read_user(16)
print("PVD id:", pvd[0:6])
print("volume id:", pvd[40:72].decode('ascii', 'replace').strip())
vol_space = struct.unpack_from('<I', pvd, 80)[0]
print("volume space (sectors):", vol_space)

# root dir record at offset 156
root = pvd[156:156+34]
root_lba = struct.unpack_from('<I', root, 2)[0]
root_size = struct.unpack_from('<I', root, 10)[0]
print("root dir LBA:", root_lba, "size:", root_size)

def walk_dir(lba, dsize, depth=0, path=""):
    data = read_user(lba, (dsize + 2047) // 2048)
    off = 0
    entries = []
    while off < dsize:
        ln = data[off]
        if ln == 0:
            # move to next sector boundary
            off = (off // 2048 + 1) * 2048
            continue
        rec = data[off:off+ln]
        e_lba = struct.unpack_from('<I', rec, 2)[0]
        e_size = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        name_len = rec[32]
        name = rec[33:33+name_len].decode('ascii', 'replace')
        if name not in ('\x00', '\x01'):
            kind = 'DIR ' if flags & 2 else 'FILE'
            print(f"{'  '*depth}{kind} LBA={e_lba:>7} size={e_size:>10}  {path}/{name}")
            entries.append((name, e_lba, e_size, flags))
            if flags & 2 and depth < 4:
                walk_dir(e_lba, e_size, depth+1, path + "/" + name)
        off += ln
    return entries

entries = walk_dir(root_lba, root_size)

# dump SYSTEM.CNF if present
for name, lba, sz, fl in entries:
    if name.upper().startswith("SYSTEM.CNF"):
        print("--- SYSTEM.CNF ---")
        print(read_user(lba)[:sz].decode('ascii', 'replace'))
