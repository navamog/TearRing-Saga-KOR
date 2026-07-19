"""Hunt for the English patch's VWF renderer: width tables + lbu/0x80-compare code."""
import struct, sys, os

FILES = {
    r"D:\Works\tear\extracted\SLPS_031.77": 0x80010000 - 0x800,  # ram = off + base
    r"D:\Works\tear\extracted\H.BIN": None,
    r"D:\Works\tear\extracted\G.BIN": None,
    r"D:\Works\tear\extracted\B.BIN": None,
    r"D:\Works\tear\extracted\T.BIN": None,
    r"D:\Works\tear\extracted\E.BIN": None,
}

def width_tables(d, name):
    """Find runs of >=90 bytes each in [1,13] (proportional width table for ~0x20..0x7F)."""
    n = len(d)
    i = 0
    while i < n:
        if 1 <= d[i] <= 13:
            j = i
            while j < n and 1 <= d[j] <= 13:
                j += 1
            if j - i >= 90:
                print(f"[width?] {name} off=0x{i:X} len={j-i} head={d[i:i+24].hex(' ')}")
            i = j
        else:
            i += 1

def cmp80(d, name, base):
    """Find sltiu rX,rY,0x80 with an lbu within 6 instructions before."""
    for i in range(0, len(d) - 4, 4):
        w = struct.unpack_from("<I", d, i)[0]
        if (w >> 26) == 0x0B and (w & 0xFFFF) == 0x80:  # sltiu imm 0x80
            ctx = [struct.unpack_from("<I", d, i + k*4)[0] for k in range(-6, 1)]
            if any((c >> 26) == 0x24 for c in ctx):  # lbu nearby
                loc = f"ram=0x{i+base:08X}" if base is not None else f"off=0x{i:X}"
                print(f"[cmp80] {name} {loc}")

for fn, base in FILES.items():
    d = open(fn, "rb").read()
    name = os.path.basename(fn)
    width_tables(d, name)
    cmp80(d, name, base)
