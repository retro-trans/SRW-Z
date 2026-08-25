"""Check whether a .SEG file is an offset/size table for its matching .BIN."""
import sys
import struct
import os

seg = open(sys.argv[1], "rb").read()
binsz = os.path.getsize(sys.argv[2])
print("SEG: %s bytes   BIN: %s bytes\n" % ("{:,}".format(len(seg)), "{:,}".format(binsz)))

for i in range(0, min(len(seg), 96), 16):
    print("  %08X  %-47s %s" % (
        i, " ".join("%02X" % b for b in seg[i:i + 16]),
        "".join(chr(b) if 32 <= b < 127 else "." for b in seg[i:i + 16])))

for width, label in ((4, "u32"), (8, "u32 pairs")):
    n = len(seg) // width
    print("\n-- as %d x %s --" % (n, label))
    vals = [struct.unpack("<I", seg[i * 4:i * 4 + 4])[0] for i in range(len(seg) // 4)]
    if width == 4:
        inside = sum(1 for v in vals if 0 <= v <= binsz)
        asc = sum(1 for a, b in zip(vals, vals[1:]) if b >= a)
        print("   %d/%d values <= BIN size" % (inside, len(vals)))
        print("   %d/%d ascending" % (asc, len(vals) - 1))
        print("   first 16: %s" % " ".join("0x%X" % v for v in vals[:16]))
        print("   last 8  : %s" % " ".join("0x%X" % v for v in vals[-8:]))
