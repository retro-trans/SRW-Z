"""Apply English map names to MAP/MAPNAME.BIN.

MAPNAME.BIN is exactly N x 256 bytes: one record per stride, string at the
record start, zero padding after. Records are keyed by offset // 256 -- never
by position in a filtered list, which silently misaligns everything.

Because the tail of each record is zero padding, the real byte budget is the
whole stride minus a terminator, not just the original string length. That is
verified per record before it is used.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import Patcher
from mapnames_en import build_all

STRIDE = 256

src, dst = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "ascii"

data = open(src, "rb").read()
assert len(data) % STRIDE == 0, "not a clean %d-byte stride" % STRIDE
n = len(data) // STRIDE
print("%s: %d records of %d bytes" % (os.path.basename(src), n, STRIDE))

records = []
for i in range(n):
    base = i * STRIDE
    end = data.find(b"\x00", base, base + STRIDE)
    if end == -1:
        end = base + STRIDE
    raw = data[base:end]
    tail_clean = not any(data[end:base + STRIDE])
    records.append({
        "index": i,
        "offset": base,
        "nbytes": len(raw),
        "budget": (STRIDE - 1) if tail_clean else len(raw),
        "text": raw.decode("shift_jis", errors="replace"),
    })

dirty = [r for r in records if r["budget"] != STRIDE - 1]
print("records whose padding is not clean (budget limited): %d" % len(dirty))

english = build_all([r["text"] for r in records])
p = Patcher(data)
for r in records:
    en = english.get(r["index"])
    if not en:
        continue
    p.replace(r["offset"], r["budget"], en, mode=mode)

print("\nencoding mode: %s" % mode)
p.report()
p.save(dst)

out = open(dst, "rb").read()
print("\n=== VERIFY (patched file, records 0-13 and 30-42) ===")
for i in list(range(14)) + list(range(30, 43)):
    base = i * STRIDE
    end = out.find(b"\x00", base, base + STRIDE)
    got = out[base:end if end != -1 else base + STRIDE].decode("shift_jis", errors="replace")
    print("   [%3d] %-34s (was: %s)" % (i, got, records[i]["text"]))

print("\nsize: %d -> %d bytes (%s)"
      % (len(data), len(out), "unchanged" if len(data) == len(out) else "CHANGED"))
