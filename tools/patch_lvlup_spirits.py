# -*- coding: utf-8 -*-
"""Level-up popup: pin the Spirits column in place.

The popup builder (label refs 0x4418E0 'Skills' -> code ~0x343298) fills
its draw list via 0x34C590 in two loops. Skills pass a FIXED column X
(base+0x50). Spirits compute  X = base+0x136 + s16 at spirit_entry+36  -
a per-spirit horizontal adjustment sized for the JAPANESE names; with the
English names some entries carry stale/garbage values, drawing 'Trust' /
'Resolve' on top of the Skills column (user report, state D41A1F10).

Fix: one word - the delay-slot  addu a3,v0,v1  at 0x343630 becomes
daddu a3,v0,zero, so every spirit renders at the column base, exactly like
the Skills column style.

Usage: patch_lvlup_spirits.py <iso> [--revert]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
VA = 0x343630
ORIG = 0x00433821          # addu  a3,v0,v1
PATCH = 0x2447FFE2         # addiu a3,v0,-30 (fixed offset = the
                           # original correct Strike position; plain 0
                           # sat ~30px right of the column - user note)


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    off = 455 * 2048 + (VA - VBASE + FOFF)
    with open(iso_path, "r+b") as iso:
        iso.seek(off)
        cur = struct.unpack("<I", iso.read(4))[0]
        want, put = (PATCH, ORIG) if revert else (ORIG, PATCH)
        if cur == put:
            print("already set")
            return
        # 0x0040382D = the 0.8.1.8 zero-offset variant, re-patchable
        assert cur in (want, 0x0040382D), "unexpected %08x at %#x" % (cur, VA)
        iso.seek(off)
        iso.write(struct.pack("<I", put))
        print("va %#x: %08x -> %08x" % (VA, want, put))


if __name__ == "__main__":
    main()
