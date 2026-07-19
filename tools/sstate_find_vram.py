import gzip, struct, sys
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix
from PIL import Image

state = gzip.decompress(open(r"D:\Works\tear\ePSXe1925K\sstates\SLPS_031.77.000", "rb").read())

# atlas 1A_BMP pixel data (128 bytes/row, 256 rows) from WINTIM.AR
ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")
idx = ix.build_index()
lba, size, _ = idx["/I1/WINTIM.AR"]
d = ix.read_user(lba, size)
off = 8
n = struct.unpack_from("<I", d, 0)[0]
for _ in range(n):
    es = struct.unpack_from("<I", d, off)[0]
    nm = d[off+4:off+20].split(b"\x00")[0]
    end = struct.unpack_from("<I", d, off+20)[0]
    if nm == b"1A_BMP.TIM":
        atlas = d[end-es:end]
        break
    off += 24
apx = atlas[64:]  # pixel bytes, row stride 128

# use a busy row (row 20 has 'A' glyph strokes)
row = 20
sig = apx[row*128:(row+1)*128]
# find all matches, then verify VRAM stride: next atlas row at +2048 in state
pos = 0
hits = []
while True:
    j = state.find(sig, pos)
    if j < 0:
        break
    # verify: atlas row+1 should appear at j+2048 (VRAM stride 1024px*2B)
    nxt = apx[(row+1)*128:(row+2)*128]
    if state[j+2048:j+2048+128] == nxt:
        hits.append(j)
    pos = j + 1
print("VRAM-stride-verified matches:", [hex(x) for x in hits])

for j in hits[:3]:
    # this is VRAM row 'row_in_atlas' at x=640. atlas top-left is VRAM (640,256).
    # j corresponds to VRAM (640, 256+row). vram_base = j - ((256+row)*1024 + 640)*2
    vbase = j - ((256 + row) * 1024 + 640) * 2
    print(f"  match {hex(j)} -> vram_base {hex(vbase)}")

    sp = r"C:\Users\neokl\AppData\Local\Temp\claude\D--Works-tear\d9a29a20-62a7-4351-9309-1431c070df24\scratchpad"
    def render4(base, xw, y, ww, h, out):
        img = Image.new("L", (ww*4, h)); p = img.load()
        for r in range(h):
            for c in range(ww):
                o = base + ((y+r)*1024 + (xw+c))*2
                v = struct.unpack_from("<H", state, o)[0]
                for k in range(4):
                    p[c*4+k, r] = ((v >> (k*4)) & 0xF) * 17
        img.save(out)
    def render16(base, x, y, w, h, out):
        img = Image.new("RGB", (w, h)); p = img.load()
        for r in range(h):
            for c in range(w):
                o = base + ((y+r)*1024 + (x+c))*2
                v = struct.unpack_from("<H", state, o)[0]
                p[c, r] = ((v&31)<<3, ((v>>5)&31)<<3, ((v>>10)&31)<<3)
        img.save(out)
    render4(vbase, 768, 256, 64, 128, f"{sp}\\vram_page0.png")
    render4(vbase, 832, 256, 64, 128, f"{sp}\\vram_page1.png")
    render4(vbase, 896, 256, 64, 128, f"{sp}\\vram_page2.png")
    render4(vbase, 640, 256, 64, 128, f"{sp}\\vram_atlas.png")
    render16(vbase, 0, 0, 512, 256, f"{sp}\\vram_fb.png")
    break
