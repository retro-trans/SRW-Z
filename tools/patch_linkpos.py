# -*- coding: utf-8 -*-
"""Fix glossary-link (and any segment) X drift with the VWF font.

ROOT CAUSE (found live via PINE glyph/position logging, 2026-08-19):
The dialogue drawer splits a line into segments at the 《》 link markers and
draws each segment separately.  After each segment it advances the pen as

    0x22163c:  srl  a0,v0,1        # v0 = strlen(segment) -> char count
    0x221640:  mult v1,a0          # v1 = style advance (21) -> count*21
    0x221644:  addu s4,s4,v1       # x += count * 21   (FIXED PITCH!)

With the VWF (English glyphs advance 13, not 21) every segment after a marker
drifted right by 8px per preceding English character - the growing gap the
link showed before its term.

THE FIX: the glyph renderer already writes the TRUE proportional end-X of the
drawn segment back to its state block at 0x46E340 (s1+0x10 export, verified in
the blit at 0x13abd0).  So simply load that instead of multiplying:

    lui   at,0x47
    lh    v1,-7360(at)             # v1 = true end X (0x46E340)
    daddu s4,v1,zero               # x  = true end X

Verified live in-game via PINE hot-patch: link term + underline + post-link
text all render flush (screenshots analysis/lab_fix1.png / lab_fix3.png).
This instruction pair exists at exactly ONE site in the ELF - no siblings.

Usage: patch_linkpos.py <src.elf> <dst.elf>
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
PATCH = {
    0x22163C: 0x3C010047,   # lui   at,0x47        (was: srl  a0,v0,1)
    0x221640: 0x8423E340,   # lh    v1,-7360(at)   (was: mult v1,a0)
    0x221644: 0x0060A02D,   # daddu s4,v1,zero     (was: addu s4,s4,v1)
}
ORIG = {0x22163C: 0x00022042, 0x221640: 0x00641818, 0x221644: 0x0283A021}


def apply(data):
    data = bytearray(data)
    for va, new in PATCH.items():
        off = FOFF + (va - VBASE)
        cur = struct.unpack_from("<I", data, off)[0]
        assert cur in (ORIG[va], new), \
            "unexpected instr %08x at %#x" % (cur, va)
        struct.pack_into("<I", data, off, new)
    return bytes(data)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "wb").write(apply(open(src, "rb").read()))
    print("linkpos patch applied:", dst)


if __name__ == "__main__":
    main()
