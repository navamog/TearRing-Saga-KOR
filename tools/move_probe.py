import sys
sys.path.insert(0, r"D:\Works\tear\tools")
from img_patch import apply
from cd_edcecc import verify_image_sectors
import iso_extract as ix

d = open(r"D:\Works\tear\extracted\MG1\GEVMSG08.MES", "rb").read()
i = d.find(b"What's the matter?")
print("target at file offset", hex(i), repr(d[i:i+18]))
probe = bytes.fromhex("88EA88EA88EA88408841")  # 亜亜亜 + 한글
apply(r"D:\Works\tear\build\tear_kr_test.img", [(232173, i, probe)])

ix.f = open(r"D:\Works\tear\build\tear_kr_test.img", "rb")
chk = ix.read_user(232173, i + 32)
print("patched region:", chk[i-4:i+20].hex(" "))
verify_image_sectors(r"D:\Works\tear\build\tear_kr_test.img", [232173 + i // 2048])
