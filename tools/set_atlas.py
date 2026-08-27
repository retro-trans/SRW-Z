# -*- coding: utf-8 -*-
"""Write a 69x72-byte glyph atlas into the image's font cave.

The atlas patch_hwfont stamps into the master font lives at 0x78A5B0 and is
exactly 4968 bytes. Swapping it changes the letterforms only - the stamper, the
advance hook and everything else are untouched.

RERUN patch_vwf_widths.py afterwards (--revert then apply): the advance table is
measured FROM the atlas, so a new face needs new advances.

Usage: set_atlas.py <iso> <atlas.bin> [--write]
"""
import sys

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ELF_LBA, ELF_SIZE = 455, 3471624
# 0x78A5B0 is the stamper's OWN source pointer:
#   0x78a304  lui t5,0x78 ; ori t5,t5,0xa5b0
# An earlier guess of 0x78A5B3 was 3 bytes (one row) late, which
# shifted every written glyph down a row with the previous glyph's
# last row on top - it invalidated the BIZ UDGothic A/B in 0.8.87.
ATLAS_VA, NART, GB = 0x78A5B0, 69, 72


def foff(va):
    return CAVE_FOFF + (va - CAVE_VA)


def main():
    iso, src = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    new = open(src, "rb").read()
    if len(new) != NART * GB:
        raise SystemExit("atlas must be %d bytes, got %d" % (NART * GB, len(new)))
    f = open(iso, "r+b" if write else "rb")
    f.seek(ELF_LBA * 2048)
    elf = bytearray(f.read(ELF_SIZE))
    old = bytes(elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB])
    diff = sum(1 for g in range(NART)
               if old[g * GB:(g + 1) * GB] != new[g * GB:(g + 1) * GB])
    print("glyphs that differ: %d of %d" % (diff, NART))
    if not diff:
        print("identical - nothing to do")
        return
    if not write:
        print("\n(dry run - pass --write to apply)")
        return
    elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB] = new
    f.seek(ELF_LBA * 2048)
    f.write(bytes(elf))
    f.close()
    g = open(iso, "rb"); g.seek(ELF_LBA * 2048); back = g.read(ELF_SIZE); g.close()
    assert back == bytes(elf), "readback mismatch"
    print("written and verified")


if __name__ == "__main__":
    main()
