"""Proper GIFtag scan of a decompressed PCSX2 GS dump -> glyph sprite coords.

Scan the whole buffer for GIFtags in PACKED mode (FLG=0) whose REGS descriptor
list contains UV(3) and XYZ2(5) -- i.e. textured-sprite draws. Parse the
following NLOOP*NREG PACKED qwords with the CORRECT bit layouts:
  PACKED XYZ2 (reg 5): X = bits 0..15, Y = bits 32..47   (12.4 fixed -> /16 px)
  PACKED UV   (reg 3): U = bits 0..13, V = bits 32..45    (10.4 fixed -> /16 px)
  PACKED PRIM (reg 0): PRIM = bits 0..10 (prim type = low 3 bits; 6 = SPRITE)
Screen XY carry the GS XYOFFSET (commonly 2048px); we auto-detect and subtract.
"""
import sys, struct
from collections import Counter

data = open(sys.argv[1], "rb").read()
n = len(data)

REGNAME = {0: "PRIM", 1: "RGBAQ", 2: "ST", 3: "UV", 4: "XYZF2", 5: "XYZ2",
           0x0d: "XYZ3", 0x0e: "AD", 0x0f: "NOP"}

sprites = []   # (x1,y1,x2,y2,u1,v1,u2,v2)
i = 0
scanned = 0
while i + 16 <= n:
    lo = struct.unpack("<Q", data[i:i + 8])[0]
    hi = struct.unpack("<Q", data[i + 8:i + 16])[0]
    nloop = lo & 0x7FFF
    flg = (lo >> 58) & 3
    nreg = (lo >> 60) & 0xF
    pre = (lo >> 46) & 1
    prim = (lo >> 47) & 0x7FF
    if nreg == 0:
        nreg = 16
    # candidate textured-sprite GIFtag: PACKED, small nloop/nreg, REGS has UV+XYZ2
    if flg == 0 and 1 <= nloop <= 8 and 2 <= nreg <= 6:
        regs = [(hi >> (4 * k)) & 0xF for k in range(nreg)]
        if 3 in regs and 5 in regs:
            # parse NLOOP*NREG packed qwords following the tag
            body = i + 16
            need = nloop * nreg * 16
            if body + need <= n:
                verts = []
                curuv = None
                ok = True
                for it in range(nloop):
                    for r in regs:
                        q = data[body:body + 16]
                        body += 16
                        qlo = struct.unpack("<Q", q[:8])[0]
                        qhi = struct.unpack("<Q", q[8:])[0]
                        if r == 3:      # UV
                            u = (qlo & 0x3FFF) / 16.0
                            v = ((qlo >> 32) & 0x3FFF) / 16.0
                            curuv = (u, v)
                        elif r == 5:    # XYZ2
                            x = (qlo & 0xFFFF) / 16.0
                            y = ((qlo >> 32) & 0xFFFF) / 16.0
                            if curuv:
                                verts.append((curuv[0], curuv[1], x, y))
                if len(verts) >= 2:
                    for j in range(0, len(verts) - 1, 2):
                        u1, v1, x1, y1 = verts[j]
                        u2, v2, x2, y2 = verts[j + 1]
                        sprites.append((x1, y1, x2, y2, u1, v1, u2, v2))
                i = body
                scanned += 1
                continue
    i += 4

print("sprite-GIFtags parsed: %d ; sprites: %d" % (scanned, len(sprites)))
if not sprites:
    sys.exit()

# auto-detect XYOFFSET: the common minimum X (rounded to 2048 boundary)
xs = sorted(s[0] for s in sprites)
off = 2048.0 if xs and xs[0] > 1500 else 0.0
print("assumed XYOFFSET = %.0f px\n" % off)

# glyph sprites: small, in a horizontal row (the dialogue text)
rows = Counter(round(s[1] - off) for s in sprites)
textrows = [y for y, c in rows.items() if c >= 4 and 200 <= y <= 460]
print("candidate text rows (screen Y, count):",
      sorted((y, rows[y]) for y in textrows))

print("\n=== glyph sprites (first text row) — dst vs src ===")
print(" dstX1  dstX2  dstW   dstY   |  srcU1  srcU2  srcW   srcV")
if textrows:
    ty = min(textrows)
    row = sorted((s for s in sprites if round(s[1] - off) == ty), key=lambda s: s[0])
    prev = None
    for x1, y1, x2, y2, u1, v1, u2, v2 in row[:30]:
        pitch = "" if prev is None else "  pitch=%.1f" % (x1 - prev)
        prev = x1
        print("%6.1f %6.1f  %4.1f  %6.1f  | %6.1f %6.1f  %4.1f  %6.1f%s"
              % (x1 - off, x2 - off, x2 - x1, y1 - off, u1, u2, u2 - u1, v1, pitch))
