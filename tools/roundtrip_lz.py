"""Prove the codec: for every record in a compressed container,
decompress -> recompress (same flags) -> decompress again and demand byte
equality, then check the recompressed blob fits the original slot.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

src = open(sys.argv[1], "rb").read()
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9

offsets = []
i = 0
recs = []
while i < len(src):
    j = i
    while j < len(src) and src[j] == 0:
        j += 1
    if j >= len(src):
        break
    total, flags, stream_at = banlz.parse_header(src, j)
    if total is None:
        break
    data, nxt = banlz.decompress_stream(src, stream_at, total)
    recs.append((j, nxt, flags, data))
    i = nxt
    if len(recs) >= limit:
        break

print("%d records parsed" % len(recs))
ok = bigger = 0
for k, (start, end, flags, data) in enumerate(recs):
    slot = (recs[k + 1][0] if k + 1 < len(recs) else len(src)) - start
    blob = banlz.compress_record(data, flags)
    rt, _ = banlz.decompress_record(blob)
    if rt != data:
        print("  [%d] ROUND-TRIP MISMATCH" % k)
        continue
    ok += 1
    orig = end - start
    tag = ""
    if len(blob) > slot:
        bigger += 1
        tag = "  << EXCEEDS SLOT"
    if k < 6 or tag:
        print("  [%3d] dec %8d  orig %7d  mine %7d  slot %7d%s"
              % (k, len(data), orig, len(blob), slot, tag))

print("\nround-trip exact: %d/%d" % (ok, len(recs)))
print("records exceeding their slot: %d" % bigger)
