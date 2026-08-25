"""Experiment: halve the glyph OUTLINE offsets globally.

The flush draws each glyph's outline as multiple offset sprites, adjusted by
`addiu t1,t1,+/-0x10` (X) and `addiu t1,t1,+/-8` (Y) across a long block
(~0x13AFB0..0x13B300). At tight (12px) pitch those ~16px outline satellites
land on neighboring glyphs -> mess. Halving them (0x10->8, 8->4) pulls the
outline in so it hugs the (now 12px) glyph.

This is GLOBAL (affects Japanese outline too, making it thinner). Test whether
Japanese still reads well. Scans a bounded range and only rewrites addiu t1,t1
immediates whose value is exactly +/-0x10 or +/-8.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
LO = 0x13AFB0
HI = 0x13B300

src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, "rb").read())
n = 0
for va in range(LO, HI, 4):
    o = FOFF + (va - VBASE)
    w = struct.unpack("<I", data[o:o+4])[0]
    op = w >> 26
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = w & 0xFFFF
    # addiu t1,t1,imm   (t1 = reg 9)
    if op == 0x09 and rs == 9 and rt == 9:
        s = imm - 0x10000 if imm >= 0x8000 else imm
        if s in (0x10, -0x10, 8, -8):
            ns = s // 2
            neww = (0x09 << 26) | (9 << 21) | (9 << 16) | (ns & 0xFFFF)
            data[o:o+4] = struct.pack("<I", neww)
            n += 1
open(dst, "wb").write(data)
print("outline offsets halved: %d sites in %#x..%#x" % (n, LO, HI))
