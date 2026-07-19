"""Check a translation JSON against the 223-slot font budget for one MES file.
A slot = one distinct character (hangul syllable, space, or punctuation) rendered on bank0/bank1.
Reports the count and, if over budget, the least-frequent characters to trim."""
import sys, json, collections

SLOT_LIMIT = 382  # JP base: bank0 page0 byte 0x01-0xFF (255) + bank1 page1 byte 0x01-0x7F (127)

def check(tr_json):
    raw = json.load(open(tr_json, encoding="utf-8"))
    freq = collections.Counter()
    for k, arr in raw.items():
        if k.startswith("_"):
            continue
        if isinstance(arr, dict):
            arr = arr.get("kr", [])
        for s in arr:
            if s:
                for ch in s:
                    freq[ch] += 1
    distinct = len(freq)
    print(f"{tr_json}")
    print(f"  distinct chars (slots): {distinct} / {SLOT_LIMIT}  -> {'OK' if distinct <= SLOT_LIMIT else 'OVER by ' + str(distinct - SLOT_LIMIT)}")
    if distinct > SLOT_LIMIT:
        rare = freq.most_common()[:-31:-1]
        print("  least-frequent chars (candidates to trim/replace):")
        print("   ", " ".join(f"{c!r}x{n}" for c, n in rare))
    return distinct

if __name__ == "__main__":
    for p in sys.argv[1:]:
        check(p)
