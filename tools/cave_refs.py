# -*- coding: utf-8 -*-
"""Is the renderer cave at 0x121810 really dead code in the ORIGINAL ELF?

Precedent: the previous cave at 0x188470 was believed dead because the scan
checked jal and pointers only - the original reaches it with a plain `j`, and
overwriting it soft-locked chapter 1's first scene event. The chapter-9 ->
next-map black screen happens in EVERY English build including v1.0, which fits
the same shape: a chapter that is the first to need something we overwrote.

Scan the UNPATCHED ELF for every way the cave range can be referenced:
  - j / jal targets landing inside it
  - branch targets from just outside
  - 32-bit data words holding an address inside it
  - lui/addiu and lui/lw immediate pairs forming such an address
"""
import os
import struct
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LO, HI = 0x121808, 0x1230C0

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    WORK, "hwbuild", "base_ui.elf")
if not os.path.exists(path):
    for alt in ("orig.elf", "SLPS_258.87", "base_ui2.elf"):
        q = os.path.join(WORK, "hwbuild", alt)
        if os.path.exists(q):
            path = q
            break
print("scanning: %s" % os.path.basename(path))
d = open(path, "rb").read()

phoff = struct.unpack_from("<I", d, 0x1C)[0]
phnum = struct.unpack_from("<H", d, 0x2C)[0]
phes = struct.unpack_from("<H", d, 0x2A)[0]
segs = []
for i in range(phnum):
    o = phoff + i * phes
    typ, off, va, pa, fsz, msz = struct.unpack_from("<IIIIII", d, o)
    if typ == 1 and fsz:
        segs.append((off, va, fsz))
print("PT_LOAD: %s" % [("0x%X" % v, "0x%X" % f) for _, v, f in segs])


def va(fo):
    for off, v, fsz in segs:
        if off <= fo < off + fsz:
            return v + (fo - off)
    return None


jt = jalt = data = luipair = branch = 0
hits = []
for off, v, fsz in segs:
    for p in range(off, off + fsz - 4, 4):
        w = struct.unpack_from("<I", d, p)[0]
        op = w >> 26
        # j / jal
        if op in (2, 3):
            tgt = ((va(p) or 0) & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
            if LO <= tgt < HI:
                hits.append(("jal" if op == 3 else "j", va(p), tgt))
                if op == 3:
                    jalt += 1
                else:
                    jt += 1
        # branches
        elif op in (4, 5, 6, 7, 1, 20, 21, 22, 23):
            off16 = w & 0xFFFF
            if off16 & 0x8000:
                off16 -= 0x10000
            tgt = (va(p) or 0) + 4 + off16 * 4
            if LO <= tgt < HI and not (LO <= (va(p) or 0) < HI):
                hits.append(("branch", va(p), tgt))
                branch += 1
        # raw data word
        if LO <= w < HI and not (LO <= (va(p) or 0) < HI):
            hits.append(("data", va(p), w))
            data += 1

# lui/addiu and lui/lw pairs
for off, v, fsz in segs:
    for p in range(off, off + fsz - 8, 4):
        w1 = struct.unpack_from("<I", d, p)[0]
        if (w1 >> 26) != 0x0F:            # lui
            continue
        hi16 = w1 & 0xFFFF
        for q in (p + 4, p + 8):
            if q + 4 > off + fsz:
                break
            w2 = struct.unpack_from("<I", d, q)[0]
            op2 = w2 >> 26
            if op2 not in (0x09, 0x23, 0x2B):   # addiu, lw, sw
                continue
            lo16 = w2 & 0xFFFF
            if lo16 & 0x8000:
                lo16 -= 0x10000
            addr = (hi16 << 16) + lo16
            if LO <= addr < HI:
                hits.append(("lui-pair", va(p), addr))
                luipair += 1

print("\nreferences INTO 0x%X..0x%X" % (LO, HI))
print("  j        : %d" % jt)
print("  jal      : %d" % jalt)
print("  branch   : %d" % branch)
print("  data word: %d" % data)
print("  lui pair : %d" % luipair)
print("  TOTAL    : %d" % len(hits))
for kind, src, tgt in hits[:25]:
    print("   %-9s from %s -> 0x%X"
          % (kind, ("0x%08X" % src) if src else "?", tgt))
