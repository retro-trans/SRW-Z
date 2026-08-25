"""Dump one block's raw tail so the true index/pool boundary is visible."""
import sys
import os
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc

data = open(sys.argv[1], "rb").read()
seg = srvc.read_seg(open(sys.argv[2], "rb").read())
bi = int(sys.argv[3])
start, limit = seg[bi], seg[bi + 1]
print("block %d: 0x%X..0x%X (%d bytes)" % (bi, start, limit, limit - start))
print("header: %s" % " ".join("%02X" % b for b in data[start:start + 16]))
grp = struct.unpack("<H", data[start + 2:start + 4])[0]
n_a, n_b = struct.unpack("<HH", data[start + 4:start + 8])
print("  +2 groups=%d   +4=%d  +6=%d" % (grp, n_a, n_b))

# Grouping table is (u16 first, u8 count, u8 tag). If +4 is the line count,
# the index should start once the grouping entries are exhausted.
print("\n-- first 12 grouping entries --")
for k in range(12):
    o = start + 8 + k * 4
    first, cnt, tag = struct.unpack("<HBB", data[o:o + 4])
    print("   [%2d] first=%-5d count=%-4d tag=0x%02X" % (k, first, cnt, tag))

# Show the region where the index should be: 8-byte pairs with small offsets
print("\n-- scanning for the (id, offset) index --")
for cand in range(start + 8, min(start + 4096, limit - 8), 4):
    ident, off = struct.unpack("<II", data[cand:cand + 8])
    if off == 0 and 0x8000 <= ident <= 0xFFFF:
        print("   candidate index start 0x%X: id=0x%X off=0" % (cand, ident))
        for k in range(6):
            i2, o2 = struct.unpack("<II", data[cand + k * 8:cand + k * 8 + 8])
            print("      [%d] id=0x%04X off=%d" % (k, i2, o2))
        pool = cand + n_a * 8
        print("   if n1=%d -> pool at 0x%X" % (n_a, pool))
        print("   pool bytes: %s" % " ".join("%02X" % b for b in data[pool:pool + 32]))
        try:
            s = data[pool:data.find(b"\x00", pool)]
            print("   first string: %r" % s.decode("shift_jis"))
        except Exception as e:
            print("   decode failed: %s" % e)
        break
