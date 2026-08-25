"""Identify the game's font asset and work out its glyph geometry.

A fixed-size bitmap font shows up as: low entropy, a strong stride in the
non-empty data, and a total size that divides cleanly by plausible glyph
byte-sizes (width*height*bpp/8).
"""
import sys
import collections

path = sys.argv[1]
data = open(path, "rb").read()
print("size: %s bytes" % "{:,}".format(len(data)))
print("first 16 bytes: %r" % data[:16])
print()

for i in range(0, 96, 16):
    print("  %08X  %-47s %s" % (
        i,
        " ".join("%02X" % b for b in data[i:i + 16]),
        "".join(chr(b) if 32 <= b < 127 else "." for b in data[i:i + 16])))

print("\n-- container magics --")
for m in (b"TIM2", b"CLUT", b"TEX0", b"FONT", b"\x10\x00\x00\x00"):
    print("   %-20r %d" % (m, data.count(m)))

print("\n-- byte histogram (top 8) --")
c = collections.Counter(data)
for b, n in c.most_common(8):
    print("   0x%02X : %14s (%5.1f%%)" % (b, "{:,}".format(n), 100.0 * n / len(data)))

print("\n-- candidate glyph geometries (must divide evenly) --")
for w, h in ((12, 12), (16, 16), (20, 20), (24, 24), (32, 32), (16, 12), (24, 16)):
    for bpp in (1, 4, 8):
        gsz = w * h * bpp // 8
        if gsz and len(data) % gsz == 0:
            print("   %2dx%-2d @%dbpp = %4d bytes/glyph -> %6d glyphs"
                  % (w, h, bpp, gsz, len(data) // gsz))
