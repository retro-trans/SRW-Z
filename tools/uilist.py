"""List ELF strings in an offset window, shortest first -- menu labels and
system messages live together in one region."""
import sys
import json

rows = json.load(open(sys.argv[1], encoding="utf-8"))
lo = int(sys.argv[2], 16)
hi = int(sys.argv[3], 16)
maxlen = int(sys.argv[4]) if len(sys.argv) > 4 else 24
top = int(sys.argv[5]) if len(sys.argv) > 5 else 60

sel = [r for r in rows if lo <= r["offset"] < hi and len(r["text"]) <= maxlen]
sel.sort(key=lambda r: r["offset"])
print("%d strings in 0x%X..0x%X with <= %d chars\n" % (len(sel), lo, hi, maxlen))
for r in sel[:top]:
    print("  0x%08X (%3dB) %s" % (r["offset"], r["nbytes"], r["text"].replace("\n", " / ")))
