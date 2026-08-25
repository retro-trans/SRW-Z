"""Dump every SJIS string in a decompressed stage record, numbered, with byte
budgets -- the working document for translation."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strdump

path = sys.argv[1]
rows = strdump.dump(path, min_len=2, min_jp=0.25, min_chars=1)
data = open(path, "rb").read()

# extend each entry with the zero-padding after it (extra byte budget)
for r in rows:
    end = r["offset"] + r["nbytes"]
    pad = 0
    while end + pad + 1 < len(data) and data[end + pad + 1] == 0 and pad < 64:
        pad += 1
    r["budget"] = r["nbytes"] + pad

print("%d strings, %s bytes text" % (len(rows), "{:,}".format(sum(r["nbytes"] for r in rows))))
if len(sys.argv) > 2:
    json.dump(rows, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("written to %s" % sys.argv[2])

for i, r in enumerate(rows):
    txt = r["text"].replace("\n", "\\n")
    print("[%03d] 0x%06X %3dB %s" % (i, r["offset"], r["nbytes"], txt))
