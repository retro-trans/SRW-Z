"""GS-dump parse handling GIF A+D mode (native GS register formats).

Scan for A+D GIFtags (FLG=0, NREG=1, REGS[0]=0xE), then read NLOOP qwords, each
= (data:u64 at bytes 0..7, reg:u8 at byte 8). Native formats:
  XYZ2 (0x05): X=bits0..15, Y=bits16..31   (12.4 fixed -> /16 px)
  XYZF2(0x04): X=bits0..15, Y=bits16..31
  UV   (0x03): U=bits0..13, V=bits16..29    (10.4 fixed -> /16 px)
  PRIM (0x00): prim type = bits0..2 (6=SPRITE)
  XYOFFSET_1/2 (0x18/0x1A): OFX=bits0..15, OFY=bits32..47 (screen offset, /16)
Build sprites from consecutive UV+XYZ2 vertices; report the text row.
"""
import sys, struct
from collections import Counter

data = open(sys.argv[1], "rb").read()
n = len(data)

writes = []   # (reg, data) in program order
i = 0
tags = 0
while i + 16 <= n:
    lo = struct.unpack("<Q", data[i:i + 8])[0]
    hi = struct.unpack("<Q", data[i + 8:i + 16])[0]
    nloop = lo & 0x7FFF
    flg = (lo >> 58) & 3
    nreg = (lo >> 60) & 0xF
    if flg == 0 and nreg == 1 and (hi & 0xF) == 0xE and 1 <= nloop <= 2048:
        body = i + 16
        if body + nloop * 16 <= n:
            good = True
            tmp = []
            for k in range(nloop):
                q = data[body + k * 16: body + k * 16 + 16]
                reg = q[8]
                if reg > 0x63:
                    good = False
                    break
                dqlo = struct.unpack("<Q", q[:8])[0]
                tmp.append((reg, dqlo))
            if good:
                writes.extend(tmp)
                tags += 1
                i = body + nloop * 16
                continue
    i += 4

print("A+D GIFtags: %d ; register writes: %d" % (tags, len(writes)))

# find XYOFFSET
ofx = ofy = 0
for reg, d in writes:
    if reg in (0x18, 0x1A):
        ofx = (d & 0xFFFF) / 16.0
        ofy = ((d >> 32) & 0xFFFF) / 16.0
print("XYOFFSET: ofx=%.1f ofy=%.1f" % (ofx, ofy))

# build vertices (UV then XYZ2), then sprites
verts = []
curuv = None
for reg, d in writes:
    if reg == 0x03:      # UV
        curuv = ((d & 0x3FFF) / 16.0, ((d >> 16) & 0x3FFF) / 16.0)
    elif reg in (0x04, 0x05):   # XYZ(F)2
        x = (d & 0xFFFF) / 16.0
        y = ((d >> 16) & 0xFFFF) / 16.0
        verts.append((curuv[0] if curuv else 0, curuv[1] if curuv else 0, x, y))

sprites = []
for j in range(0, len(verts) - 1, 2):
    u1, v1, x1, y1 = verts[j]
    u2, v2, x2, y2 = verts[j + 1]
    sprites.append((x1, y1, x2, y2, u1, v1, u2, v2))
print("vertices: %d ; sprites: %d" % (len(verts), len(sprites)))

# screen coords = raw - offset
def sx(x): return x - ofx
def sy(y): return y - ofy

rows = Counter(round(sy(s[1])) for s in sprites if 2 <= abs(s[2]-s[0]) <= 40)
textrows = sorted((y, c) for y, c in rows.items() if c >= 5)
print("\ntext-row candidates (screenY,count):", textrows[-8:])

if textrows:
    ty = textrows[-1][0]           # densest row
    row = sorted((s for s in sprites if round(sy(s[1])) == ty and 2 <= abs(s[2]-s[0]) <= 40),
                 key=lambda s: s[0])
    print("\n=== glyph row at screenY=%d — DEST vs SOURCE ===" % ty)
    print(" dstX1  dstX2  dstW    | srcU1  srcU2  srcW   srcV1  srcV2   pitch")
    prev = None
    for x1, y1, x2, y2, u1, v1, u2, v2 in row[:32]:
        p = "" if prev is None else "%.1f" % (sx(x1) - prev)
        prev = sx(x1)
        print("%6.1f %6.1f  %5.1f  | %5.1f %5.1f  %5.1f  %5.1f %5.1f   %s"
              % (sx(x1), sx(x2), x2 - x1, u1, u2, u2 - u1, v1, v2, p))
