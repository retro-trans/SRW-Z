# -*- coding: utf-8 -*-
"""Raise every advance in the VWF width table up to a minimum.

patch_vwf_widths stores (advance-1) per glyph, measured as ink_right+2 with only
a max(4,..) floor. Narrow glyphs (i, l, !) come out very tight. This floors them
to MIN so they get comfortable trailing room; wide glyphs (already above MIN) are
untouched. Pair with normalize_atlas <in> <out> MIN, which centres the same
glyphs so the added room sits evenly on both sides. Run AFTER patch_vwf_widths.

Usage: floor_advance_table.py <iso> <min_advance> [--write]
"""
import struct
import sys

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ELF_LBA, ELF_SIZE = 455, 3471624
TABLE_VA, NART = 0x78B960, 69      # reclaimed underline-stub space (stores advance-1)


def foff(va):
    return CAVE_FOFF + (va - CAVE_VA)


def main():
    iso, mn = sys.argv[1], int(sys.argv[2])
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(ELF_LBA * 2048)
    elf = bytearray(f.read(ELF_SIZE))
    base = foff(TABLE_VA)
    tbl = list(elf[base:base + NART])
    if all(v == 0 for v in tbl):
        print("advance table is empty - run patch_vwf_widths first")
        f.close()
        return
    floorv = mn - 1                    # table holds advance-1
    raised = 0
    for i in range(NART):
        if tbl[i] < floorv:
            tbl[i] = floorv
            raised += 1
    print("floored %d/%d advances to min %d (advances now %d..%d)"
          % (raised, NART, mn, min(tbl) + 1, max(tbl) + 1))
    if not write:
        print("\n(dry run - pass --write)")
        f.close()
        return
    elf[base:base + NART] = bytes(tbl)
    f.seek(ELF_LBA * 2048)
    f.write(bytes(elf))
    f.close()
    print("advance table written")


main()
