"""Why do most blocks fail to parse? Report per-block: marker present, the
n1/n2 counts, whether an index validated, and how much Japanese it contains.
"""
import sys
import os
import struct
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc
from sjisscan import find_runs

data = open(sys.argv[1], "rb").read()
seg = srvc.read_seg(open(sys.argv[2], "rb").read())

stats = collections.Counter()
examples = {}
jp_unparsed = 0
jp_parsed = 0

for bi in range(len(seg) - 1):
    start, limit = seg[bi], seg[bi + 1]
    chunk = data[start:limit]
    jp = sum(len(t) for _, t in find_runs(chunk, min_chars=4))

    if chunk[:4] != srvc.MARKER:
        key = "no marker"
    else:
        n1, n2 = struct.unpack("<HH", chunk[4:8])
        if n1 == 0 or n2 == 0:
            key = "counts zero (n1=%d n2=%d)" % (n1, n2)
        else:
            hit = None
            for cand in range(start + 8, limit - 8, 4):
                if srvc._try_index(data, cand, n1, n2, limit):
                    hit = cand
                    break
            key = "index OK" if hit else "index NOT FOUND"
    stats[key] += 1
    if key != "index OK":
        jp_unparsed += jp
        if key not in examples and jp > 50:
            examples[key] = (bi, start, limit, jp)
    else:
        jp_parsed += jp

print("=== BLOCK OUTCOMES ===")
for k, v in stats.most_common():
    print("  %-32s %4d blocks" % (k, v))

print("\nJapanese chars in parsed blocks   : %s" % "{:,}".format(jp_parsed))
print("Japanese chars in UNPARSED blocks : %s" % "{:,}".format(jp_unparsed))

print("\n=== EXAMPLE UNPARSED BLOCK WITH TEXT ===")
for key, (bi, start, limit, jp) in examples.items():
    print("\n[%s] block %d  0x%X..0x%X  (%d bytes, %d JP chars)"
          % (key, bi, start, limit, limit - start, jp))
    for i in range(start, min(start + 96, limit), 16):
        print("  %08X  %-47s %s" % (
            i, " ".join("%02X" % b for b in data[i:i + 16]),
            "".join(chr(b) if 32 <= b < 127 else "." for b in data[i:i + 16])))
