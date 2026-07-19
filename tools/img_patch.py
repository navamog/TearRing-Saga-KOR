"""Apply byte patches to user-data of a raw Mode2/2352 image, fixing EDC/ECC.

Usage: img_patch.py <image> <patchspec>...
  patchspec: LBA:offset_in_file_bytes:hexbytes   (offset relative to file start, file starts at LBA)
Patches the image IN PLACE (work on a copy).
"""
import sys, struct
sys.path.insert(0, r"D:\Works\tear\tools")
from cd_edcecc import sector_fix

SECTOR, USER_OFF, USER_LEN = 2352, 24, 2048

def apply(img_path, patches):
    """patches: list of (start_lba, byte_offset_from_file_start, bytes)"""
    f = open(img_path, "r+b")
    touched = set()
    for start_lba, off, data in patches:
        while data:
            lba = start_lba + off // USER_LEN
            in_off = off % USER_LEN
            n = min(len(data), USER_LEN - in_off)
            f.seek(lba * SECTOR)
            raw = bytearray(f.read(SECTOR))
            raw[USER_OFF + in_off: USER_OFF + in_off + n] = data[:n]
            sector_fix(raw)
            f.seek(lba * SECTOR)
            f.write(raw)
            touched.add(lba)
            print(f"patched LBA {lba} +0x{in_off:X} len {n}")
            data = data[n:]
            off += n
    f.close()
    return touched

if __name__ == "__main__":
    img = sys.argv[1]
    patches = []
    for spec in sys.argv[2:]:
        lba_s, off_s, hex_s = spec.split(":")
        patches.append((int(lba_s), int(off_s, 16), bytes.fromhex(hex_s)))
    apply(img, patches)
