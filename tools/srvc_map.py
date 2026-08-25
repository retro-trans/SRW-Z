"""Map the block layout of BTL/SRVC.BIN.

Observed so far: the file opens with 00 4F 00 00 and that word recurs, so it
looks like a sequence of blocks, each = [header][entry table][index][strings].
This script locates the block boundaries and dumps enough of each header to
pin the format down.
"""
import sys
import struct

path = sys.argv[1]
data = open(path, "rb").read()
print("size: %s bytes\n" % "{:,}".format(len(data)))

MARK = b"\x00\x4F\x00\x00"
hits = []
pos = data.find(MARK)
while pos != -1 and len(hits) < 4000:
    hits.append(pos)
    pos = data.find(MARK, pos + 1)

print("marker 00 4F 00 00 occurs %d times" % len(hits))
print("first 24 offsets:", ["0x%X" % h for h in hits[:24]])
if len(hits) > 1:
    gaps = [b - a for a, b in zip(hits, hits[1:])]
    print("first 20 gaps:", gaps[:20])
print()

# Dump the region between the file start and the first text run so we can see
# where the entry table ends and the (id, offset) index begins.
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from sjisscan import find_runs

first_text = find_runs(data[:0x4000], min_chars=4)[0][0]
print("first text run at 0x%X" % first_text)
print("\n=== BYTES 0x100 .. first text ===")
for i in range(0x100, first_text + 16, 16):
    chunk = data[i:i + 16]
    print("  %08X  %-47s %s" % (
        i, " ".join("%02X" % b for b in chunk),
        "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)))

# Interpret the 4-byte entry table at 0x08 as (u16 idx, u8 type, u8 tag)
print("\n=== ENTRY TABLE at 0x08 as (u16 idx, u8 type, u8 tag) ===")
tags = {}
for off in range(8, min(first_text, 0x2000), 4):
    idx, typ, tag = struct.unpack("<HBB", data[off:off + 4])
    tags[(typ, tag)] = tags.get((typ, tag), 0) + 1
for (typ, tag), n in sorted(tags.items(), key=lambda kv: -kv[1]):
    print("   type=0x%02X tag=0x%02X : %d entries" % (typ, tag, n))
