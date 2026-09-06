# -*- coding: utf-8 -*-
"""Double the UI glyph-sprite pool (319 -> 639 glyphs per flush).

The menu text blit (0x13A290) stamps every glyph into a pool of 32-byte
structs allocated once at init:

    0x13A094  addiu a1,zero,0x2800      ; 19D058(a0, 0x2800) -> 0x46E388 pool base
    0x13AB28  addiu v0,zero,0x13F       ; cap: when count == 319 the NEXT glyph
                                        ; overwrites the last slot (silently lost)

The pool is flushed only when a string is drawn with a packet handle; UI
elements without their own packet (the Bazaar buy popup, layer with no packet)
append to the frame's pool and are drawn last, so on a screen whose other text
already fills ~300 slots the popup loses its tail ("「Nanomachine Unit' wi").
Japanese text never reached the cap (kanji are dense); English does. Live
proof (2026-09-06, PINE dump at the stalled popup): all 319 structs in use,
draw-list x positions correct, moving the item or widening the box changed
nothing - only the count mattered.

Fix: allocation 0x2800 -> 0x5000 and cap 0x13F -> 0x27F (both immediates).
The other 0x13F literals in the ELF (0x22C7xx dialogue engine etc.) are left
alone: they keep their own limit and can never exceed the larger buffer.

Usage: patch_glyph_pool.py <iso> [--write] [--revert]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
ELF_LBA, SECTOR = 455, 2048
ALLOC_SITE = 0x13A094      # addiu a1,zero,0x2800
CAP_SITE = 0x13AB28        # addiu v0,zero,0x13F
OLD_SIZE, NEW_SIZE = 0x2800, 0x5000
OLD_CAP, NEW_CAP = 0x13F, 0x27F
assert NEW_SIZE // 32 == NEW_CAP + 1 and OLD_SIZE // 32 == OLD_CAP + 1


def foff(va): return FOFF + (va - VBASE)
def addiu(rt, rs, imm): return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def main():
    iso = sys.argv[1]; write = "--write" in sys.argv; revert = "--revert" in sys.argv
    A1, V0, ZERO = 5, 2, 0
    pairs = ((ALLOC_SITE, addiu(A1, ZERO, OLD_SIZE), addiu(A1, ZERO, NEW_SIZE)),
             (CAP_SITE, addiu(V0, ZERO, OLD_CAP), addiu(V0, ZERO, NEW_CAP)))
    with open(iso, "r+b" if write else "rb") as f:
        base = ELF_LBA * SECTOR
        state = []
        for va, old, new in pairs:
            f.seek(base + foff(va)); cur = struct.unpack("<I", f.read(4))[0]
            st = "original" if cur == old else "patched" if cur == new else "UNKNOWN %08x" % cur
            state.append(st); print("0x%X: %s" % (va, st))
        if any(s.startswith("UNKNOWN") for s in state): return 1
        if not write:
            print("(dry run)"); return 0
        for va, old, new in pairs:
            f.seek(base + foff(va)); f.write(struct.pack("<I", old if revert else new))
        f.flush()
        ok = True
        for va, old, new in pairs:
            f.seek(base + foff(va)); ok &= struct.unpack("<I", f.read(4))[0] == (old if revert else new)
        print("%s; read-back %s" % ("reverted" if revert else "written", ok))
    return 0


if __name__ == "__main__":
    sys.exit(main())
