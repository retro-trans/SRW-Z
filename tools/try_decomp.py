"""Decompress records from a file and validate against known text fragments."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

src = open(sys.argv[1], "rb").read()
recs = banlz.decompress_all(src)

print("%s: %d record(s)" % (os.path.basename(sys.argv[1]), len(recs)))
outdir = sys.argv[2] if len(sys.argv) > 2 else None
for k, (off, data) in enumerate(recs[:200]):
    if data is None:
        print("  [%d] %s" % (k, off))
        continue
    print("  [%d] input 0x%06X -> %s bytes" % (k, off, "{:,}".format(len(data))))
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "rec%03d.bin" % k), "wb") as f:
            f.write(data)

# validation: the repaired stage-1 text must appear intact
CHECKS = [
    "月面ルテチウム基地を襲撃するエゥーゴ",
    "グローリー・スター",
    "バルゴラ",
    "迎え撃つ",
]
blob = b"".join(d for _, d in recs if d)
print()
for c in CHECKS:
    print("  %-24s %s" % (c, "FOUND" if c.encode("shift_jis") in blob else "missing"))
