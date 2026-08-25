"""Solve the block layout: pool = start + 8 + G*4 + B*8 + B*8.

B is the line count from the header (+4). G (the grouping-table entry count)
is unknown, so brute-force it per block and see which value makes the pool
decode as clean Shift-JIS that tiles to the end of the block.
"""
import sys
import os
import struct
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc

data = open(sys.argv[1], "rb").read()
seg = srvc.read_seg(open(sys.argv[2], "rb").read())


def pool_ok(pool, limit, need):
    """Do `need` null-terminated valid-SJIS strings tile from pool to limit?"""
    pos = pool
    count = 0
    while pos < limit and count < need:
        end = data.find(b"\x00", pos, limit)
        if end == -1:
            return False
        raw = data[pos:end]
        if raw:
            try:
                raw.decode("shift_jis")
            except UnicodeDecodeError:
                return False
        count += 1
        pos = end + 1
    if count != need:
        return False
    # only zero padding may remain
    return limit - pos <= 64 and not any(data[pos:limit])


solved = collections.Counter()
report = []
for bi in range(len(seg) - 1):
    start, limit = seg[bi], seg[bi + 1]
    if data[start:start + 2] != srvc.MARKER or limit - start < 16:
        continue
    A, B, C = struct.unpack("<HHH", data[start + 2:start + 8])
    if B == 0:
        continue
    hits = []
    for G in range(0, 400):
        pool = start + 8 + G * 4 + B * 16
        if pool >= limit:
            break
        if pool_ok(pool, limit, B):
            hits.append(G)
    if hits:
        solved[hits[0]] += 1
        if len(report) < 10:
            report.append((bi, A, B, C, hits[:4]))
    else:
        solved["none"] += 1

print("=== WHICH GROUPING-TABLE SIZE G WORKS? ===")
for g, n in solved.most_common(12):
    print("   G=%-6s %4d blocks" % (g, n))

print("\n=== SAMPLE BLOCKS ===")
for bi, A, B, C, hits in report:
    print("   block %-4d +2=%-5d lines=%-5d +6=%-5d  G candidates %s"
          % (bi, A, B, C, hits))
