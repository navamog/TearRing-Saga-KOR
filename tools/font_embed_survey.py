"""Survey which MES files embed the ASCII font block, at what offset, and detect compression."""
import gzip, struct, sys, os
sys.path.insert(0, r"D:\Works\tear\tools")
import iso_extract as ix

# reference font block from a known MES (GEVMSG08 @ 0x2BD8, 12288 bytes)
ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")  # any copy fine for reading orig-not; use original image
ix.f = open(r"D:\Works\tear\티어링사가(eng).img", "rb")
idx = ix.build_index()

ref = ix.read_user(*idx["/MG1/GEVMSG08.MES"][:2])[0x2BD8:0x2BD8+12288]
# a distinctive middle row of the font (row with glyphs) as quick probe
probe = ref[74*128:75*128]

mes = sorted(k for k, v in idx.items() if k.endswith(".MES") and not v[2] & 2)
print(f"total MES: {len(mes)}")
embed = []
noembed = []
for k in mes:
    lba, size, _ = idx[k]
    d = ix.read_user(lba, size)
    j = d.find(probe)
    if j >= 0:
        # font block starts at j - 74*128
        fb = j - 74*128
        # verify full block matches ref
        full = d[fb:fb+12288] == ref
        embed.append((k, fb, full))
    else:
        noembed.append(k)

print(f"embed font (probe found): {len(embed)}, no-embed: {len(noembed)}")
# offset distribution
from collections import Counter
offs = Counter(fb for _, fb, _ in embed)
print("font block offsets:", dict(offs))
full_match = sum(1 for _, _, f in embed if f)
print(f"identical full block: {full_match}/{len(embed)}")
print("no-embed sample:", noembed[:20])
