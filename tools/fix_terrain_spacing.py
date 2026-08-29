# -*- coding: utf-8 -*-
"""Give the terrain row its 24px spaces back, so the ranks line up again.

The unit panel builds its terrain row from the ELF string

    空　陸　海　宇        (0x33D9E0, three fullwidth spaces 0x8140)

and paints the rank letters over the gaps. patch_hwfont deliberately advances
0x8140 by 13px rather than 24, because in English prose THAT space is the word
space. Here that is wrong: each of the three spaces pulls the kanji after it
11px to the left while the ranks stay where the japanese layout put them, so
the gap before each rank grows across the row - 11px, then 22, then 33. It
reads as "the rank letters are shifted right", and it gets worse rightward.

Nothing about the row was ever ours: the string is byte-identical to the
japanese disc. Only the advance changed underneath it.

patch_micro_glyphs already built the fix for a different instance of exactly
this problem - a BLANK full-width cell at private code 0x85DB, created so the
white spirit strip and the grey one would share an advance path. Swapping the
three 0x8140 for 0x85DB restores a 24px advance and is byte-neutral, so the
string still fits its 16-byte slot.

Usage: fix_terrain_spacing.py <iso> [--revert]
"""
import os
import sys

ELF_LBA, SECTOR = 455, 2048
# The string appears ELEVEN times in the ELF, not once. Patching only the
# first (0x33D9E0, the parts screen) left the unit panel untouched and the row
# still drifting - found by dumping EE RAM from a save state and seeing ten
# copies still holding 0x8140 while the patched one sat right beside them.
JP = bytes.fromhex("8bf3 8140 97a4 8140 8a43 8140 8946".replace(" ", ""))
EN = bytes.fromhex("8bf3 85db 97a4 85db 8a43 85db 8946".replace(" ", ""))


def main():
    iso = sys.argv[1]
    revert = "--revert" in sys.argv
    want, other = (JP, EN) if revert else (EN, JP)
    base = ELF_LBA * SECTOR
    with open(iso, "r+b") as f:
        f.seek(base)
        elf = f.read(3471624)
        hits = []
        o = elf.find(other)
        while o >= 0:
            hits.append(o)
            o = elf.find(other, o + 1)
        if not hits:
            print("already %s - nothing to do"
                  % ("reverted" if revert else "patched"))
            return
        for o in hits:
            f.seek(base + o)
            f.write(want)
        print("patched %d copies: %s"
              % (len(hits), ", ".join("0x%06X" % h for h in hits)))
    print("terrain row spaces: %s"
          % ("0x85DB -> 0x8140 (13px word space)" if revert
             else "0x8140 -> 0x85DB (blank full-width cell, 24px advance)"))
    print("string stays %d bytes; slot is 16" % len(want))


if __name__ == "__main__":
    main()
