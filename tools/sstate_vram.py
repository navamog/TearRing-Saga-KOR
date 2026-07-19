"""Extract VRAM from an ePSXe save state and dump regions to PNG.

ePSXe .000 = gzip. Decompressed: "ePSXe" + ver + gameid, then PSX RAM (2MB),
GPU/SPU freeze blocks including 1MB VRAM (1024x512x16bit).

We locate VRAM by searching for the known 1A_BMP atlas bytes (from WINTIM.AR)
at VRAM (640,256), then compute base. VRAM (x16,y) byte offset = (y*1024 + x)*2.
"""
import sys, gzip, struct
from PIL import Image

def load_state(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw

def find_vram_base(state, atlas_bytes):
    """Return file offset where VRAM (0,0) begins, using a known atlas signature."""
    # atlas sits at VRAM (640,256): offset_in_vram = (256*1024 + 640)*2
    vram_off_of_atlas = (256 * 1024 + 640) * 2
    idx = state.find(atlas_bytes)
    if idx < 0:
        return None
    return idx - vram_off_of_atlas

def vram_pixel_offset(base, x16, y):
    return base + (y * 1024 + x16) * 2

def dump_region(state, base, x, y, w, h, out, mode="16"):
    """x,y in 16bit-pixel VRAM coords. For 4bpp textures pass mode='4' and x in 16bit units (each unit=4 px)."""
    if mode == "16":
        img = Image.new("RGB", (w, h))
        p = img.load()
        for row in range(h):
            for col in range(w):
                off = vram_pixel_offset(base, x + col, y + row)
                v = struct.unpack_from("<H", state, off)[0]
                r = (v & 31) << 3; g = ((v >> 5) & 31) << 3; b = ((v >> 10) & 31) << 3
                p[col, row] = (r, g, b)
        img.save(out)
    else:  # 4bpp: w = number of 16bit words across; each word = 4 pixels
        pw = w * 4
        img = Image.new("L", (pw, h))
        p = img.load()
        for row in range(h):
            for col in range(w):
                off = vram_pixel_offset(base, x + col, y + row)
                v = struct.unpack_from("<H", state, off)[0]
                for k in range(4):
                    idx = (v >> (k * 4)) & 0xF
                    p[col * 4 + k, row] = idx * 17
        img.save(out)
    print(f"saved {out}")

if __name__ == "__main__":
    import iso_extract as ix
    state = load_state(sys.argv[1])
    print("state size", len(state))
    # get atlas signature from WINTIM.AR 1A_BMP first pixel row (16 bytes)
    ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")
    idx = ix.build_index()
    lba, size, _ = idx["/I1/WINTIM.AR"]
    d = ix.read_user(lba, size)
    off = 8
    n = struct.unpack_from("<I", d, 0)[0]
    bmp = None
    for _ in range(n):
        esize = struct.unpack_from("<I", d, off)[0]
        name = d[off+4:off+20].split(b"\x00")[0]
        end = struct.unpack_from("<I", d, off+20)[0]
        if name == b"1A_BMP.TIM":
            bmp = d[end-esize:end]
            break
        off += 24
    sig = bmp[64:64+32]  # first 32 bytes of atlas pixel data
    base = find_vram_base(state, sig)
    print("VRAM base offset:", hex(base) if base else "NOT FOUND")
    if base is not None:
        sp = r"C:\Users\neokl\AppData\Local\Temp\claude\D--Works-tear\d9a29a20-62a7-4351-9309-1431c070df24\scratchpad"
        # page0 font at VRAM (768,256), 4bpp: 64 words wide (256px), 256 tall
        dump_region(state, base, 768, 256, 64, 256, sp + r"\vram_page0.png", mode="4")
        dump_region(state, base, 832, 256, 64, 256, sp + r"\vram_page1.png", mode="4")
        dump_region(state, base, 640, 256, 64, 256, sp + r"\vram_atlas1a.png", mode="4")
        # full VRAM overview 16bit
        dump_region(state, base, 0, 0, 1024, 512, sp + r"\vram_full.png", mode="16")
