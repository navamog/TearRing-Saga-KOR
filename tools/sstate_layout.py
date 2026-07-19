import gzip, struct, sys
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix

state = gzip.decompress(open(r"D:\Works\tear\ePSXe1925K\sstates\SLPS_031.77.000", "rb").read())
exe = open(r"D:\Works\tear\extracted\SLPS_031.77", "rb").read()

sig = exe[0x800:0x800+64]
i = state.find(sig)
print("EXE code at state offset", hex(i) if i >= 0 else "NO")
ram_base = i - 0x10000
print("RAM base:", hex(ram_base), "RAM end:", hex(ram_base + 0x200000))

ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")
idx = ix.build_index()
lba, size, _ = idx["/I1/WINTIM.AR"]
d = ix.read_user(lba, size)
off = 8
n = struct.unpack_from("<I", d, 0)[0]
atlas = None
for _ in range(n):
    es = struct.unpack_from("<I", d, off)[0]
    nm = d[off+4:off+20].split(b"\x00")[0]
    end = struct.unpack_from("<I", d, off+20)[0]
    if nm == b"1A_BMP.TIM":
        atlas = d[end-es:end]
        break
    off += 24
asig = atlas[64:64+48]
pos = ram_base + 0x200000
found = []
while True:
    j = state.find(asig, pos)
    if j < 0:
        break
    found.append(j)
    pos = j + 1
print("atlas matches after RAM:", [hex(x) for x in found[:8]])
# each atlas match at VRAM (640,256) -> vram_off = (256*1024+640)*2 = 0x80200
for j in found[:8]:
    vbase = j - 0x80200
    print(f"  match {hex(j)} -> vram_base {hex(vbase)} (offset from RAM end {hex(vbase - (ram_base+0x200000))})")
