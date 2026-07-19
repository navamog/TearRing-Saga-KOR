"""Find lui/lo16 reference pairs to a RAM address in MIPS code.
Usage: find_ref.py <ram_hex> [file] — scans EXE by default, also overlay BINs (offset only)."""
import struct, sys, glob, os

target = int(sys.argv[1], 16)
hi = (target + 0x8000) >> 16  # lui value accounting for signed lo16
lo = target & 0xFFFF
lo_signed = lo - 0x10000 if lo >= 0x8000 else lo

files = sys.argv[2:] or [r"D:\Works\tear\extracted\SLPS_031.77"] + glob.glob(r"D:\Works\tear\extracted\*.BIN")

for fn in files:
    d = open(fn, "rb").read()
    name = os.path.basename(fn)
    is_exe = name.startswith("SLPS")
    for i in range(0, len(d) - 4, 4):
        w = struct.unpack_from("<I", d, i)[0]
        if (w >> 26) == 0x0F and (w & 0xFFFF) == hi:  # lui rX, hi
            rt = (w >> 16) & 31
            # look ahead up to 8 instructions for imm == lo using rt as base/source
            for k in range(1, 9):
                if i + k*4 + 4 > len(d):
                    break
                w2 = struct.unpack_from("<I", d, i + k*4)[0]
                op2 = w2 >> 26
                rs2 = (w2 >> 21) & 31
                imm2 = w2 & 0xFFFF
                if rs2 == rt and imm2 == lo and op2 in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                    loc = f"ram=0x{i - 0x800 + 0x80010000:08X}" if is_exe else f"off=0x{i:X}"
                    print(f"{name} {loc} lui+{k} op=0x{op2:02X}")
                    break
