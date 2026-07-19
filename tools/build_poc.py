"""Build the hangul PoC onto build/tear_kr_test.img.

- Hook: Krom2RawAdd BIOS stub (RAM 0x800A5860, EXE file off 0x96060) -> j cave
- Cave: RAM 0x800CCE00 (EXE file off 0xBD600, zero padding at EXE tail)
- Font: RAM 0x800CCE80 (EXE file off 0xBD680), glyphs for SJIS 0x8840('한'), 0x8841('글')
- Text probe B: MB0.MES (LBA 232064) offset 0x49: " do " -> 88 40 88 41
  (Probe A already applied: offset 0x43 "Eugen," -> 88EA x3 '亜亜亜')
"""
import sys
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from render_glyph import render_glyph, to_bytes

IMG = r"D:\Works\tear\build\tear_kr_test.img"
EXE_LBA = 746
MES_LBA = 232064

# ---- mini assembler ----
def R(n): return n
ZERO, AT, V0, V1, A0, A1, A2, A3 = range(8)
T0, T1, T2, T3, T4, T5, T6, T7 = range(8, 16)
RA = 31

def i_type(op, rs, rt, imm): return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
def r_type(rs, rt, rd, sa, fn): return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn
def SRL(rd, rt, sa): return r_type(0, rt, rd, sa, 0x02)
def SLL(rd, rt, sa): return r_type(0, rt, rd, sa, 0x00)
def ADDIU(rt, rs, imm): return i_type(9, rs, rt, imm)
def SLTIU(rt, rs, imm): return i_type(0x0B, rs, rt, imm)
def ANDI(rt, rs, imm): return i_type(0x0C, rs, rt, imm)
def ORI(rt, rs, imm): return i_type(0x0D, rs, rt, imm)
def LUI(rt, imm): return i_type(0x0F, 0, rt, imm)
def BEQ(rs, rt, off): return i_type(4, rs, rt, off)
def BNE(rs, rt, off): return i_type(5, rs, rt, off)
def MULT(rs, rt): return r_type(rs, rt, 0, 0, 0x18)
def MFLO(rd): return r_type(0, 0, rd, 0, 0x12)
def ADDU(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x21)
def SUBU(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x23)
def JR(rs): return r_type(rs, 0, 0, 0, 0x08)
def J(target): return (2 << 26) | ((target >> 2) & 0x3FFFFFF)
NOP = 0

CAVE = 0x800CCE00
FONT = 0x800CCE80

# branch offsets: imm = (target - (branch_pc + 4)) / 4
code = [
    SRL(T0, A0, 8),            # CE00 lead
    ADDIU(T0, T0, -0x88),      # CE04
    SLTIU(T1, T0, 7),          # CE08 lead in 0x88..0x8E?
    BEQ(T1, ZERO, (0x60 - 0x10) // 4),   # CE0C -> BIOS @CE60
    ANDI(T2, A0, 0xFF),        # CE10 (delay) lo
    SLTIU(T1, T2, 0x40),       # CE14
    BNE(T1, ZERO, (0x60 - 0x1C) // 4),   # CE18 lo<0x40 -> BIOS
    SLTIU(T1, T2, 0x80),       # CE1C (delay) t1 = lo<0x80
    BNE(T1, ZERO, (0x2C - 0x24) // 4),   # CE20 -> SKIP @CE2C
    ADDIU(T2, T2, -0x40),      # CE24 (delay, both paths)
    ADDIU(T2, T2, -1),         # CE28 only lo>=0x80
    ADDIU(T3, ZERO, 188),      # CE2C SKIP
    MULT(T0, T3),              # CE30
    MFLO(T3),                  # CE34
    ADDU(T3, T3, T2),          # CE38 glyph index
    SLL(T4, T3, 5),            # CE3C *32
    SLL(T5, T3, 1),            # CE40 *2
    SUBU(T4, T4, T5),          # CE44 *30
    LUI(V0, FONT >> 16),       # CE48
    ORI(V0, V0, FONT & 0xFFFF),# CE4C
    ADDU(V0, V0, T4),          # CE50
    JR(RA),                    # CE54
    NOP,                       # CE58
    NOP,                       # CE5C
    ADDIU(T2, ZERO, 0xB0),     # CE60 BIOS fallthrough
    JR(T2),                    # CE64
    ADDIU(T1, ZERO, 0x51),     # CE68
    NOP,                       # CE6C
]
code_bytes = b"".join(w.to_bytes(4, "little") for w in code)
assert len(code_bytes) <= 0x80

stub = [J(CAVE), NOP]
stub_bytes = b"".join(w.to_bytes(4, "little") for w in stub)

font_bytes = to_bytes(render_glyph("한", size=14)) + to_bytes(render_glyph("글", size=14))
assert len(font_bytes) == 60

patches = [
    (EXE_LBA, 0x96060, stub_bytes),          # hook the Krom2RawAdd stub
    (EXE_LBA, 0xBD600, code_bytes),          # cave code
    (EXE_LBA, 0xBD680, font_bytes),          # font
    (MES_LBA, 0x49, bytes.fromhex("88408841")),  # probe B text
]
apply(IMG, patches)
print("PoC built.")
