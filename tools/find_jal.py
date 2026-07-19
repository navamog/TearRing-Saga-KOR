"""Find jal/j callers of given RAM targets across binaries. Usage: find_jal.py <ram_hex>... [--files f1 f2]"""
import struct, sys, glob, os

args = sys.argv[1:]
if "--files" in args:
    i = args.index("--files")
    rams = [int(x, 16) for x in args[:i]]
    files = args[i+1:]
else:
    rams = [int(x, 16) for x in args]
    files = [r"D:\Works\tear\extracted\SLPS_031.77"] + glob.glob(r"D:\Works\tear\extracted\*.BIN")

want = {}
for ram in rams:
    idx = (ram >> 2) & 0x3FFFFFF
    want[0x0C000000 | idx] = ("jal", ram)
    want[0x08000000 | idx] = ("j", ram)

for fn in files:
    d = open(fn, "rb").read()
    base = os.path.basename(fn)
    for i in range(0, len(d) - 4, 4):
        w = struct.unpack_from("<I", d, i)[0]
        if w in want:
            kind, ram = want[w]
            # RAM addr valid only for EXE with known load; print raw offset
            exe_ram = i - 0x800 + 0x80010000 if base == "SLPS_031.77" else None
            loc = f"ram=0x{exe_ram:08X}" if exe_ram else f"off=0x{i:X}"
            print(f"{base} {loc} {kind} 0x{ram:08X}")
