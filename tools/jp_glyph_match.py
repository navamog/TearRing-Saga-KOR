"""Auto-identify JP game glyphs by matching against PC-font renders.

Input:  trdata/jp_glyphs.bin (128B 4bpp cells) + jp_glyphs.json
Output: trdata/jp_glyph_map_auto.json  [{char, score, alts} per glyph index]

Game 4bpp CLUT: 0 = transparent, 1 = darkest body, 2..15 progressively lighter.
Coverage = 0 for idx 0 else (16-idx)/15.

Candidates: every cp932 double-byte char (JIS X 0208 lv1+2), ASCII 0x20-0x7E,
halfwidth katakana. Rendered supersampled like the game font, over a small grid
of (size, dx, dy) configs; calibration picks the best config on frequent glyphs.
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageFont, ImageDraw

TR = r"D:\Works\tear\trdata"
FONTS = [("gothic", r"C:\Windows\Fonts\msgothic.ttc"),
         ("mincho", r"C:\Windows\Fonts\msmincho.ttc"),
         ("meiryo", r"C:\Windows\Fonts\meiryo.ttc"),
         ("meiryob", r"C:\Windows\Fonts\meiryob.ttc"),
         ("yugothm", r"C:\Windows\Fonts\YuGothM.ttc"),
         ("yugothb", r"C:\Windows\Fonts\YuGothB.ttc"),
         ("bizudr", r"C:\Windows\Fonts\BIZ-UDGothicR.ttc"),
         ("bizudb", r"C:\Windows\Fonts\BIZ-UDGothicB.ttc"),
         ("kyokar", r"C:\Windows\Fonts\UDDigiKyokashoN-R.ttc"),
         ("kyokab", r"C:\Windows\Fonts\UDDigiKyokashoN-B.ttc")]
SS = 4

def load_game_glyphs():
    raw = open(os.path.join(TR, "jp_glyphs.bin"), "rb").read()
    n = len(raw) // 128
    arr = np.zeros((n, 256), dtype=np.float32)
    for i in range(n):
        cellb = raw[i*128:(i+1)*128]
        px = np.zeros(256, dtype=np.float32)
        for j, b in enumerate(cellb):
            lo, hi = b & 0xF, b >> 4   # 4bpp little: low nibble = left pixel
            px[j*2] = 0.0 if lo == 0 else (16 - lo) / 15.0
            px[j*2+1] = 0.0 if hi == 0 else (16 - hi) / 15.0
        arr[i] = px
    return arr

def candidates():
    chars = []
    for hi in list(range(0x81, 0xA0)) + list(range(0xE0, 0xEB)):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try:
                ch = bytes([hi, lo]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if len(ch) == 1:
                chars.append(ch)
    chars += [chr(c) for c in range(0x20, 0x7F)]
    chars += [chr(c) for c in range(0xFF61, 0xFFA0)]  # halfwidth katakana
    return chars

MARGIN = 4  # px margin so negative shifts don't clip strokes

def render_batch(chars, font_path, size, dx, dy):
    font = ImageFont.truetype(font_path, size * SS)
    box = (16 + 2 * MARGIN) * SS
    out = np.zeros((len(chars), 256), dtype=np.float32)
    for i, ch in enumerate(chars):
        img = Image.new("L", (box, box), 0)
        ImageDraw.Draw(img).text(((MARGIN + dx) * SS, (MARGIN + dy) * SS), ch, fill=255, font=font)
        small = img.resize((16 + 2 * MARGIN, 16 + 2 * MARGIN), Image.BOX)
        crop = small.crop((MARGIN, MARGIN, MARGIN + 16, MARGIN + 16))
        out[i] = np.asarray(crop, dtype=np.float32).reshape(-1) / 255.0
    return out

def norm(m):
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1
    return m / n

def blur3(m):
    """3x3 tent blur on (n,256) binary/coverage rows; tolerates 1px stroke offsets."""
    img = m.reshape(-1, 16, 16)
    out = np.zeros_like(img)
    k = {(0, 0): 1.0, (0, 1): .5, (0, -1): .5, (1, 0): .5, (-1, 0): .5,
         (1, 1): .25, (1, -1): .25, (-1, 1): .25, (-1, -1): .25}
    for (dy, dx), w in k.items():
        ys, ye = max(dy, 0), 16 + min(dy, 0)
        xs, xe = max(dx, 0), 16 + min(dx, 0)
        out[:, ys:ye, xs:xe] += w * img[:, ys - dy:ye - dy, xs - dx:xe - dx]
    return np.clip(out, 0, 1).reshape(-1, 256)

def score_matrix(G, Gn, Gb, C):
    """Cosine on blurred binary shapes (offset-tolerant) blended with strict IoU."""
    Cb = (C > 0.35).astype(np.float32)
    cos_b = norm(blur3(Gb)) @ norm(blur3(Cb)).T
    inter = Gb @ Cb.T
    aG = Gb.sum(1, keepdims=True)
    aC = Cb.sum(1)[None, :]
    union = aG + aC - inter
    union[union == 0] = 1
    iou = inter / union
    # ink-area agreement: dense blobs must not attract sparse glyphs
    ratio = np.minimum(aG, aC) / np.maximum(np.maximum(aG, aC), 1)
    return (0.7 * cos_b + 0.3 * iou) * ratio ** 0.5

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    G = load_game_glyphs()
    meta = json.load(open(os.path.join(TR, "jp_glyphs.json"), encoding="utf-8"))
    counts = np.array([g["count"] for g in meta["glyphs"]])
    print(f"game glyphs: {len(G)}")
    Gn = norm(G)
    Gb = (G > 0.35).astype(np.float32)

    chars = candidates()
    print(f"candidates: {len(chars)}")

    # calibration: per font find best (size,dx,dy) on kana vs 150 most frequent glyphs
    freq_idx = np.argsort(-counts)[:150]
    kana = [ch for ch in chars if 0x3041 <= ord(ch) <= 0x30FF] + list("。、!?…「」")
    results = []
    for fname, fpath in FONTS:
        best = (-1, None)
        for size in (13, 14, 15, 16):
            for dy in (-1, 0, 1, 2):
                for dx in (-1, 0, 1):
                    C = render_batch(kana, fpath, size, dx, dy)
                    sim = score_matrix(G[freq_idx], Gn[freq_idx], Gb[freq_idx], C)
                    mean = float(np.sort(sim.max(axis=1))[-100:].mean())
                    if mean > best[0]:
                        best = (mean, (size, dx, dy))
        results.append((best[0], fname, fpath, best[1]))
        print(f"  {fname}: best {best[1]} mean={best[0]:.4f}")
    results.sort(reverse=True)
    best_mean, fname, fpath, (size, dx, dy) = results[0]
    print(f"config: font={fname} size={size} dx={dx} dy={dy} (mean {best_mean:.4f})")

    # full match: best font, neighbor sizes and +-1px shifts, take max score
    sims = None
    for s in (size - 1, size, size + 1):
        for ddx in (dx - 1, dx, dx + 1):
            for ddy in (dy - 1, dy, dy + 1):
                C = render_batch(chars, fpath, s, ddx, ddy)
                m = score_matrix(G, Gn, Gb, C)
                sims = m if sims is None else np.maximum(sims, m)
    top3 = np.argsort(-sims, axis=1)[:, :3]

    # --- kana variant refinement (dakuten/handakuten/small forms) ---
    import unicodedata
    SMALL2BIG = dict(zip("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ",
                          "あいうえおつやゆよわアイウエオツヤユヨワカケ"))
    def group_key(ch):
        base = unicodedata.normalize("NFD", ch)[0]
        return SMALL2BIG.get(base, base)
    groups = {}
    for ch in chars:
        if 0x3041 <= ord(ch) <= 0x30F6:
            groups.setdefault(group_key(ch), set()).add(ch)
    char_pos = {ch: i for i, ch in enumerate(chars)}

    W = np.ones((16, 16), dtype=np.float32)
    W[0:8, 9:16] = 3.0   # dakuten/handakuten region (top-right)
    W = W.reshape(-1)
    def refined_score(gvec_b, cand_b):
        gw = W * blur3(gvec_b[None])[0]
        cw = W * blur3(cand_b[None])[0]
        na, nb = np.linalg.norm(gw), np.linalg.norm(cw)
        return float(gw @ cw / (na * nb)) if na and nb else 0.0

    refine_cache = {}
    def cand_renders(ch):
        if ch not in refine_cache:
            vs = []
            for s in (size - 1, size, size + 1):
                for ddx in (dx - 1, dx, dx + 1):
                    for ddy in (dy - 1, dy, dy + 1):
                        vs.append((render_batch([ch], fpath, s, ddx, ddy)[0] > 0.35).astype(np.float32))
            refine_cache[ch] = vs
        return refine_cache[ch]

    refined = 0
    for i in range(len(G)):
        best = chars[top3[i][0]]
        if not (0x3041 <= ord(best) <= 0x30F6):
            continue
        grp = groups.get(group_key(best), {best})
        if len(grp) < 2:
            continue
        gb = Gb[i]
        scored = []
        for ch in grp:
            sc = max(refined_score(gb, cb) for cb in cand_renders(ch))
            scored.append((sc, ch))
        scored.sort(reverse=True)
        if scored[0][1] != best:
            refined += 1
        top3[i][0] = char_pos[scored[0][1]]
        sims[i, top3[i][0]] = max(sims[i, top3[i][0]], scored[0][0])
    print(f"kana variant refinement changed {refined} glyphs")

    out = []
    lows = 0
    for i in range(len(G)):
        ids = top3[i]
        sc = float(sims[i, ids[0]])
        out.append({
            "char": chars[ids[0]],
            "score": round(sc, 4),
            "alts": [[chars[j], round(float(sims[i, j]), 4)] for j in ids[1:]],
            "count": int(counts[i]),
        })
        if sc < 0.85:
            lows += 1
    json.dump(out, open(os.path.join(TR, "jp_glyph_map_auto.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    scores = np.array([o["score"] for o in out])
    print(f"score dist: min={scores.min():.3f} p10={np.percentile(scores,10):.3f} "
          f"median={np.median(scores):.3f} p90={np.percentile(scores,90):.3f}")
    print(f"glyphs below 0.85: {lows}")
    print("wrote trdata/jp_glyph_map_auto.json")
