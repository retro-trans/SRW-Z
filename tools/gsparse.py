"""Scan a decompressed PCSX2 GS dump for glyph sprite coordinates.

We look for GS register writes in GIF PACKED A+D mode: each 16-byte qword is
[data:u64 LE][addr:u8 at byte 8][pad]. Registers of interest:
  0x00 PRIM   (bits 0-2 = primitive; 6 = SPRITE)
  0x01 RGBAQ  (R,G,B,A bytes)
  0x03 UV     (U bits 0-13 = 10.4 fixed; V bits 16-29)  -> source/atlas px = /16
  0x05 XYZ2   (X bits 0-15 = 12.4 fixed; Y bits 16-31)  -> screen px = /16
A textured SPRITE uses 2 vertices: (UV,XYZ2) then (UV,XYZ2). We collect
consecutive UV/XYZ2 in program order and pair them into sprites, then print the
ones in the dialogue-box screen region (bottom of the frame).
"""
import sys
import struct

data = open(sys.argv[1], "rb").read()
n = len(data)

# Walk 16-byte-aligned-ish; A+D qwords have byte[8] a valid reg and bytes 9..15 ~0.
events = []  # (kind, a, b)  kind in {PRIM,UV,XYZ2,RGBAQ}
i = 0
while i + 16 <= n:
    reg = data[i + 8]
    pad = data[i + 9:i + 16]
    if reg <= 0x0E and pad.count(0) >= 6:
        d = struct.unpack("<Q", data[i:i + 8])[0]
        if reg == 0x00:      # PRIM
            events.append(("PRIM", d & 7, d))
        elif reg == 0x01:    # RGBAQ
            events.append(("RGBA", d & 0xFF, (d >> 8) & 0xFF))
        elif reg == 0x03:    # UV
            u = (d & 0x3FFF) / 16.0
            v = ((d >> 16) & 0x3FFF) / 16.0
            events.append(("UV", u, v))
        elif reg == 0x05:    # XYZ2
            x = (d & 0xFFFF) / 16.0
            y = ((d >> 16) & 0xFFFF) / 16.0
            events.append(("XYZ2", x, y))
        i += 16
    else:
        i += 4

# pair UV+XYZ2 into vertices, then vertices into 2-vertex sprites
verts = []
lastuv = None
for k, a, b in events:
    if k == "UV":
        lastuv = (a, b)
    elif k == "XYZ2" and lastuv is not None:
        verts.append((lastuv[0], lastuv[1], a, b))  # u,v,x,y
        lastuv = None

sprites = []
for j in range(0, len(verts) - 1, 2):
    u1, v1, x1, y1 = verts[j]
    u2, v2, x2, y2 = verts[j + 1]
    sprites.append((x1, y1, x2, y2, u1, v1, u2, v2))

print("events: %d, vertices: %d, sprites(2-vert): %d" % (len(events), len(verts), len(sprites)))

# dialogue box is the lower part of a 448-tall frame; glyphs are small.
print("\n=== sprites in the dialogue region (y 300..430, width 4..40) ===")
print(" dst[x1,y1 -> x2,y2]  (w x h)      src UV[u1,v1 -> u2,v2] (w x h)")
shown = 0
for x1, y1, x2, y2, u1, v1, u2, v2 in sprites:
    dw, dh = x2 - x1, y2 - y1
    if 300 <= y1 <= 430 and 3 <= abs(dw) <= 40 and 3 <= abs(dh) <= 40:
        sw, sh = u2 - u1, v2 - v1
        print("  [%6.1f,%6.1f -> %6.1f,%6.1f] (%4.1f x%4.1f)   [%6.1f,%6.1f -> %6.1f,%6.1f] (%4.1f x%4.1f)"
              % (x1, y1, x2, y2, dw, dh, u1, v1, u2, v2, sw, sh))
        shown += 1
        if shown >= 40:
            break
