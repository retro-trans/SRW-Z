"""Filter a strdump JSON down to plausible real text and show the longest."""
import sys
import json

rows = json.load(open(sys.argv[1], encoding="utf-8"))
min_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 4
top = int(sys.argv[3]) if len(sys.argv) > 3 else 30


def kana_frac(t):
    return sum(1 for ch in t if "぀" <= ch <= "ヿ") / max(1, len(t))


keep = [r for r in rows if len(r["text"]) >= min_chars and kana_frac(r["text"]) >= 0.15]
keep.sort(key=lambda r: -len(r["text"]))
print("%d/%d strings pass (>= %d chars, kana >= 15%%)" % (len(keep), len(rows), min_chars))
print("total budget: %s bytes\n" % "{:,}".format(sum(r["nbytes"] for r in keep)))
for r in keep[:top]:
    print("  0x%08X (%3dB) %s" % (r["offset"], r["nbytes"], r["text"][:70]))

out = sys.argv[4] if len(sys.argv) > 4 else None
if out:
    json.dump(keep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nwritten to %s" % out)
