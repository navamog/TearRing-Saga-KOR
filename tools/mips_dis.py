"""Minimal MIPS I disassembler for PSX-EXE ranges. Usage: mips_dis.py <file> <load_ram_hex> <start_ram_hex> <end_ram_hex> [hdr_off_hex]"""
import struct, sys

REG = ["zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
       "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"]

def dis(w, pc):
    if w == 0: return "nop"
    op = w >> 26
    rs, rt, rd = (w>>21)&31, (w>>16)&31, (w>>11)&31
    sa = (w>>6)&31
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm >= 0x8000 else imm
    R = lambda i: REG[i]
    if op == 0:
        fn = w & 0x3F
        m = {0x20:"add",0x21:"addu",0x22:"sub",0x23:"subu",0x24:"and",0x25:"or",0x26:"xor",0x27:"nor",0x2A:"slt",0x2B:"sltu"}
        if fn in m: return f"{m[fn]} {R(rd)}, {R(rs)}, {R(rt)}"
        if fn == 0x00: return f"sll {R(rd)}, {R(rt)}, {sa}"
        if fn == 0x02: return f"srl {R(rd)}, {R(rt)}, {sa}"
        if fn == 0x03: return f"sra {R(rd)}, {R(rt)}, {sa}"
        if fn == 0x04: return f"sllv {R(rd)}, {R(rt)}, {R(rs)}"
        if fn == 0x06: return f"srlv {R(rd)}, {R(rt)}, {R(rs)}"
        if fn == 0x08: return f"jr {R(rs)}"
        if fn == 0x09: return f"jalr {R(rd)}, {R(rs)}" if rd != 31 else f"jalr {R(rs)}"
        if fn == 0x0C: return "syscall"
        if fn == 0x10: return f"mfhi {R(rd)}"
        if fn == 0x12: return f"mflo {R(rd)}"
        if fn == 0x18: return f"mult {R(rs)}, {R(rt)}"
        if fn == 0x19: return f"multu {R(rs)}, {R(rt)}"
        if fn == 0x1A: return f"div {R(rs)}, {R(rt)}"
        if fn == 0x1B: return f"divu {R(rs)}, {R(rt)}"
        return f".word 0x{w:08X}"
    if op == 1:
        nm = {0:"bltz",1:"bgez",16:"bltzal",17:"bgezal"}.get(rt, f"bcond{rt}")
        return f"{nm} {R(rs)}, 0x{pc+4+simm*4:08X}"
    if op == 2: return f"j 0x{(pc & 0xF0000000)|((w&0x3FFFFFF)<<2):08X}"
    if op == 3: return f"jal 0x{(pc & 0xF0000000)|((w&0x3FFFFFF)<<2):08X}"
    if op == 4:
        if rs == 0 and rt == 0: return f"b 0x{pc+4+simm*4:08X}"
        return f"beq {R(rs)}, {R(rt)}, 0x{pc+4+simm*4:08X}"
    if op == 5: return f"bne {R(rs)}, {R(rt)}, 0x{pc+4+simm*4:08X}"
    if op == 6: return f"blez {R(rs)}, 0x{pc+4+simm*4:08X}"
    if op == 7: return f"bgtz {R(rs)}, 0x{pc+4+simm*4:08X}"
    m = {8:"addi",9:"addiu",0x0A:"slti",0x0B:"sltiu"}
    if op in m: return f"{m[op]} {R(rt)}, {R(rs)}, {simm:#x}"
    m = {0x0C:"andi",0x0D:"ori",0x0E:"xori"}
    if op in m: return f"{m[op]} {R(rt)}, {R(rs)}, 0x{imm:X}"
    if op == 0x0F: return f"lui {R(rt)}, 0x{imm:X}"
    m = {0x20:"lb",0x21:"lh",0x23:"lw",0x24:"lbu",0x25:"lhu",0x28:"sb",0x29:"sh",0x2B:"sw",0x22:"lwl",0x26:"lwr",0x2A:"swl",0x2E:"swr"}
    if op in m: return f"{m[op]} {R(rt)}, {simm:#x}({R(rs)})"
    return f".word 0x{w:08X}"

def load(path):
    return open(path, "rb").read()

if __name__ == "__main__":
    path, loadram, start, end = sys.argv[1], int(sys.argv[2],16), int(sys.argv[3],16), int(sys.argv[4],16)
    hdr = int(sys.argv[5],16) if len(sys.argv) > 5 else 0x800
    d = load(path)
    for ram in range(start, end, 4):
        off = ram - loadram + hdr
        w = struct.unpack_from("<I", d, off)[0]
        print(f"0x{ram:08X}: {w:08X}  {dis(w, ram)}")
