"""Extract files from raw Mode2/2352 PS1 image by path (uses ISO9660 walk)."""
import struct, sys, os

IMG = r"D:\Works\tear\티어링사가(eng).img"
SECTOR, USER_OFF, USER_LEN = 2352, 24, 2048
f = open(IMG, "rb")

def read_user(lba, nbytes):
    count = (nbytes + USER_LEN - 1) // USER_LEN
    out = bytearray()
    for i in range(count):
        f.seek((lba + i) * SECTOR)
        out += f.read(SECTOR)[USER_OFF:USER_OFF + USER_LEN]
    return bytes(out[:nbytes])

def build_index():
    pvd = read_user(16, 2048)
    root = pvd[156:156+34]
    idx = {}
    def walk(lba, dsize, path):
        data = read_user(lba, dsize)
        off = 0
        while off < dsize:
            ln = data[off]
            if ln == 0:
                off = (off // 2048 + 1) * 2048
                continue
            rec = data[off:off+ln]
            e_lba = struct.unpack_from('<I', rec, 2)[0]
            e_size = struct.unpack_from('<I', rec, 10)[0]
            flags = rec[25]
            nl = rec[32]
            name = rec[33:33+nl].decode('ascii', 'replace')
            if name not in ('\x00', '\x01'):
                full = path + "/" + name.split(';')[0]
                idx[full] = (e_lba, e_size, flags)
                if flags & 2:
                    walk(e_lba, e_size, full)
            off += ln
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], "")
    return idx

if __name__ == "__main__":
    idx = build_index()
    outdir = r"D:\Works\tear\extracted"
    for want in sys.argv[1:]:
        lba, size, flags = idx[want]
        data = read_user(lba, size)
        dest = os.path.join(outdir, want.lstrip("/").replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(data)
        print(f"extracted {want} LBA={lba} size={size} -> {dest}")
