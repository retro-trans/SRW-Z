# -*- coding: utf-8 -*-
"""Make the half-width Latin font PROPORTIONAL - advance-only (v2).

v1 FAILED IN GAME (0.8.83): text collapsed into overlapping clusters. v1 changed
the per-glyph width field the stamper writes (`sh t2,0xc(s0)`, constant 0x0C) AND
nopped a test in the sprite-width cave. That field is read by more than the pen
advance, so rewriting it changed things this patch has no business changing.

v2 leaves the stamper and the sprite-width cave COMPLETELY ALONE. The width field
stays 0x0C for every glyph, so everything that reads it - including the
0x78BAC0 cave's `width == 0x0C` test that decides whether to halve the drawn
sprite - behaves exactly as it does today.

The ONLY change is the pen advance. The advance hook at 0x78BA60 ends with:

    0x78ba94  lhu   t0,0xc(s0)      ; width field (always 0x0C)
    0x78ba98  beq   zero,zero,0x78bab0
    0x78ba9c  addiu v1,t0,1         ; advance = 12+1 = 13, every glyph
    ...
    0x78bab0  addu  v1,a0,v1        ; pen += advance

Those three instructions are replaced with a jump to a trampoline that indexes a
69-byte width table by (code - 0x8540) and returns the glyph's own advance in v1.
Bold/menu glyphs (indices 69..137) are the same art dilated 1px right, so they
get +1.

Advance = ink right edge + 2, measured from the atlas actually stamped into the
master font (0x78A5B0, 72 B/glyph, 24 rows of 12px 2bpp MSB-first). Range 7..12
against a flat 13, so no advance can EXCEED the current one: no line can get
wider, the 34-column wrap stays valid, nothing can overflow.

t0 is safe to clobber - the hook saved it at 0x78BA60 and restores it at
0x78BAB4 (`lw t0,-16(sp)`).

Usage: patch_vwf_widths.py <iso> [--write] [--revert]
"""
import struct
import sys

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ELF_LBA, ELF_SIZE = 455, 3471624
ATLAS_VA, GB, ROWS, NART, CELL_W = 0x78A5B0, 72, 24, 69, 12
GAP = 2

HOOK_SITE = 0x78BA94       # lhu t0,0xc(s0)
HOOK_JOIN = 0x78BAB0       # addu v1,a0,v1
ATLAS_END = ATLAS_VA + NART * GB   # 0x78B91B - the atlas runs to here
TABLE_VA = 0x78B960        # reclaimed from the (disabled) underline stub
TRAMP_VA = 0x78B91C        # first 4-aligned byte AFTER the atlas

STOCK = (0x9608000C,       # lhu   t0,0xc(s0)
         0x10000005,       # beq   zero,zero,0x78bab0
         0x25030001)       # addiu v1,t0,1

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


def I(op, rs, rt, imm):
    return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)


def SP(rs, rt, rd, fn):
    return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | fn


def J(op, target):
    return (op << 26) | ((target >> 2) & 0x3FFFFFF)


def foff(va):
    return CAVE_FOFF + (va - CAVE_VA) if va >= CAVE_VA else va - 0x100000 + 0x1A80


def measure(elf):
    raw = elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB]
    out = []
    for g in range(NART):
        cell = raw[g * GB:(g + 1) * GB]
        right = -1
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            for x in range(CELL_W):
                if (bits >> (22 - 2 * x)) & 3:
                    right = max(right, x)
        adv = (right + GAP) if right >= 0 else CELL_W
        out.append(max(4, min(CELL_W, adv)) - 1)   # trampoline adds the +1/+2
    return bytes(out)


def build_tramp():
    """v1 = table[code-0x8540] + (1 regular | 2 bold). t0 clobbered (restored
    by the hook at 0x78BAB4). Branch target is idx+1+imm."""
    hi = (TABLE_VA + 0x8000) >> 16
    lo = TABLE_VA - (hi << 16)
    return [
        I(0x0D, "zero", "at", 0x8540),        # 0  ori   at,zero,0x8540
        SP("t0", "at", "at", 0x23),           # 1  subu  at,t0,at      (index)
        I(0x0B, "at", "v1", 0x45),            # 2  sltiu v1,at,69
        I(0x05, "v1", "zero", 3),             # 3  bne   v1,zero,->7
        I(0x0D, "zero", "v1", 1),             # 4  (delay) ori v1,zero,1
        I(0x09, "at", "at", -0x45),           # 5  addiu at,at,-69     (bold)
        I(0x0D, "zero", "v1", 2),             # 6  ori   v1,zero,2     (bold)
        I(0x0F, "zero", "t0", hi),            # 7  lui   t0,hi
        SP("t0", "at", "t0", 0x21),           # 8  addu  t0,t0,at
        I(0x24, "t0", "t0", lo),              # 9  lbu   t0,lo(t0)
        SP("t0", "v1", "v1", 0x21),           # 10 addu  v1,t0,v1
        J(0x02, HOOK_JOIN),                   # 11 j     0x78bab0
        0,                                    # 12 (delay) nop
    ]


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    revert = "--revert" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(ELF_LBA * 2048)
    elf = bytearray(f.read(ELF_SIZE))

    cur = tuple(struct.unpack_from("<I", elf, foff(HOOK_SITE + i * 4))[0]
                for i in range(3))
    patched = (J(0x02, TRAMP_VA), 0, 0)

    if revert:
        if cur != patched:
            print("not patched (site reads %s)" % [hex(x) for x in cur])
            return
        for i, w in enumerate(STOCK):
            struct.pack_into("<I", elf, foff(HOOK_SITE + i * 4), w)
        for i in range(len(build_tramp())):
            struct.pack_into("<I", elf, foff(TRAMP_VA + i * 4), 0)
        elf[foff(TABLE_VA):foff(TABLE_VA) + NART] = b"\x00" * NART
        print("reverted to fixed 13px")
    else:
        if cur != STOCK:
            print("REFUSED: %#x reads %s, expected the stock sequence %s"
                  % (HOOK_SITE, [hex(x) for x in cur], [hex(x) for x in STOCK]))
            return
        tbl = measure(elf)
        print("width table: %d entries, advance %d..%d (was a flat 13)"
              % (len(tbl), min(tbl) + 1, max(tbl) + 1))
        for va, n in ((TABLE_VA, NART), (TRAMP_VA, len(build_tramp()) * 4)):
            # An all-zero block INSIDE the atlas is not free space - it is the
            # blank rows of a glyph. v1 of this patch put the trampoline at
            # 0x78B910, 11 bytes before the atlas end, and silently ate the
            # bottom of lowercase 'z'; the emptiness check passed because those
            # rows are blank. Check the atlas bounds explicitly.
            if va < ATLAS_END and va + n > ATLAS_VA:
                print("REFUSED: %#x..%#x overlaps the glyph atlas %#x..%#x"
                      % (va, va + n, ATLAS_VA, ATLAS_END))
                return
            if va % 4 and n >= 4:
                print("REFUSED: %#x is not 4-aligned" % va)
                return
            blk = elf[foff(va):foff(va) + n]
            if any(blk):
                print("REFUSED: %#x not free (%d non-zero of %d)"
                      % (va, sum(1 for b in blk if b), n))
                return
        elf[foff(TABLE_VA):foff(TABLE_VA) + NART] = tbl
        for i, w in enumerate(build_tramp()):
            struct.pack_into("<I", elf, foff(TRAMP_VA + i * 4), w)
        struct.pack_into("<I", elf, foff(HOOK_SITE), J(0x02, TRAMP_VA))
        struct.pack_into("<I", elf, foff(HOOK_SITE + 4), 0)
        struct.pack_into("<I", elf, foff(HOOK_SITE + 8), 0)
        print("advance hook %#x -> j %#x ; table %#x ; stamper and "
              "sprite-width cave UNTOUCHED" % (HOOK_SITE, TRAMP_VA, TABLE_VA))

    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return
    f.seek(ELF_LBA * 2048)
    f.write(bytes(elf))
    f.close()
    g = open(iso, "rb"); g.seek(ELF_LBA * 2048); back = g.read(ELF_SIZE); g.close()
    assert back == bytes(elf), "readback mismatch"
    print("written and verified")


if __name__ == "__main__":
    main()
