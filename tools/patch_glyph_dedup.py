# -*- coding: utf-8 -*-
"""Reuse glyph-cache cells for repeated glyph codes within a frame (0.9.62).

The menu blit (0x13A290) rasterises every glyph into a cache TEXTURE: a cursor
(engine ctx 0x46E338/3A, mirrored in scratchpad 0x7000002C/2E) hands each
glyph a 24px cell, wrapping at 504px and 240-row pages, and when the cursor
passes 480 rows (0x13AA28) the string ABORTS - and the cursor stays there, so
every later string in the frame aborts on its first glyph. The JP engine
allocates a NEW cell for EVERY glyph occurrence; English repeats ~50 codes
hundreds of times per screen, so a busy screen (Bazaar with a long item
panel) exhausts the budget before the buy popup draws:
"「Nanomachine Unit' wi" / "「Prope" - live dump: ctx cursor y == 480.
(The 0.9.61 glyph-struct pool enlargement was NOT the limit; harmless, kept.)

Fix: per-frame code -> cell table (128 x 8 B: code, tag, penx, peny) in the
cave. Three hooks, t8/t9 (unused by the blit) + at as temporaries:
  H1 0x13AA68  allocate path (after the y-abort test): on a hit for the
               current code (0x70000060) with the current TAG, write the
               recorded cell into the glyph struct (+0 srcx, +2 srcy, +17
               page 0x24/0x2C) and jump to the struct finaliser 0x13AB20 -
               no raster-list append, no cursor advance.
  H2 0x13AAE0  just before the cursor advance: record (code, TAG, penx, peny).
  H3 0x13A260  cursor reset: TAG++ (invalidates the table). Called by the
               frame function 0x13C3B0 and by screens.
Cache contents are keyed by code only (colour/outline/size are sprite-time),
bold glyphs are distinct codes (0x8585+). A miss behaves exactly as before.

Cave (after grow_cave.py --bytes 1272, segment end 0x78C900):
  CODE 0x78C408..  TAG u16 at 0x78C3FA  TABLE 0x78C500..0x78C900
Usage: patch_glyph_dedup.py <iso> [--write] [--revert]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
CAVE_FILE, CAVE_VA = 0x34D770, 0x78A070
ELF_LBA, SECTOR = 455, 2048
H1, H1_BACK, FINAL = 0x13AA68, 0x13AA70, 0x13AB20
H2, H2_BACK = 0x13AAE0, 0x13AAE8
H3, H3_BACK = 0x13A260, 0x13A268
CODE_VA = 0x78C408          # H1 + H2
H3_VA = 0x78C3B0            # reset hook, in the gap between the popup stub and FLAG (0x78C3F8)
TAG_VA = 0x78C3FA
TABLE_VA = 0x78C500
SEG_END = 0x78C900

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


def I(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)
def SPC(rs, rt, rd, sa, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn
def J(t): return (0x02 << 26) | ((t >> 2) & 0x3FFFFFF)
def lw(rt, off, rs): return I(0x23, rs, rt, off)
def lh(rt, off, rs): return I(0x21, rs, rt, off)
def lhu(rt, off, rs): return I(0x25, rs, rt, off)
def sh(rt, off, rs): return I(0x29, rs, rt, off)
def sb(rt, off, rs): return I(0x28, rs, rt, off)
def addiu(rt, rs, imm): return I(0x09, rs, rt, imm)
def andi(rt, rs, imm): return I(0x0C, rs, rt, imm)
def ori(rt, rs, imm): return I(0x0D, rs, rt, imm)
def lui(rt, imm): return I(0x0F, 'zero', rt, imm)
def slti(rt, rs, imm): return I(0x0A, rs, rt, imm)
def beq(rs, rt, off): return I(0x04, rs, rt, off)
def bne(rs, rt, off): return I(0x05, rs, rt, off)
def srl(rd, rt, sa): return SPC('zero', rt, rd, sa, 0x02)
def sll(rd, rt, sa): return SPC('zero', rt, rd, sa, 0x00)
def xor(rd, rs, rt): return SPC(rs, rt, rd, 0, 0x26)
def addu(rd, rs, rt): return SPC(rs, rt, rd, 0, 0x21)
NOP = 0


def hl(va):
    hi = (va + 0x8000) >> 16
    return hi, va - (hi << 16)


def entry_ptr(w, code_reg, out_reg, tmp):
    """out_reg = TABLE + ((code ^ code>>7) & 0x7F) * 8   (clobbers tmp)"""
    thi, tlo = hl(TABLE_VA)
    w += [srl(tmp, code_reg, 7), xor(tmp, tmp, code_reg), andi(tmp, tmp, 0x7F), sll(tmp, tmp, 3),
          lui(out_reg, thi), addiu(out_reg, out_reg, tlo), addu(out_reg, out_reg, tmp)]


def build():
    ghi, glo = hl(TAG_VA)
    w = []
    def fix(i, target): w[i] = (w[i] & 0xFFFF0000) | ((target - (i + 1)) & 0xFFFF)
    # ---- H1: lookup ----
    h1 = len(w)
    w += [lui('at', 0x7000), lhu('t8', 0x60, 'at')]                 # t8 = code
    entry_ptr(w, 't8', 't9', 'at')                                   # t9 = entry (at clobbered)
    w += [lhu('at', 0, 't9'), bne('at', 't8', 0), NOP]              # code match?  -> MISS
    b_miss1 = len(w) - 2
    w += [lhu('at', 2, 't9'), lui('t8', ghi), lhu('t8', glo, 't8'), bne('at', 't8', 0), NOP]  # tag match?
    b_miss2 = len(w) - 2
    w += [lhu('at', 4, 't9'), sh('at', 0, 's0'),                     # srcx
          lhu('at', 6, 't9'), slti('t8', 'at', 0xF0), bne('t8', 'zero', 0), NOP]   # page?
    b_pagea = len(w) - 2
    w += [addiu('at', 'at', -0xF0), sh('at', 2, 's0'), ori('t8', 'zero', 0x2C), sb('t8', 17, 's0'), J(FINAL), NOP]
    pagea = len(w)
    w += [sh('at', 2, 's0'), ori('t8', 'zero', 0x24), sb('t8', 17, 's0'), J(FINAL), NOP]
    miss = len(w)
    w += [lui('at', 0x7000), lw('v1', 0, 'at'), J(H1_BACK), NOP]     # displaced originals
    fix(b_miss1, miss); fix(b_miss2, miss); fix(b_pagea, pagea)
    # ---- H2: record ----
    h2 = len(w)
    w += [lui('at', 0x7000), lhu('t8', 0x60, 'at')]
    entry_ptr(w, 't8', 't9', 'at')
    w += [sh('t8', 0, 't9'), lui('at', ghi), lhu('at', glo, 'at'), sh('at', 2, 't9'),
          lui('at', 0x7000), lh('t8', 0x2C, 'at'), sh('t8', 4, 't9'), lh('t8', 0x2E, 'at'), sh('t8', 6, 't9'),
          lui('at', 0x7000), lh('v0', 0x2C, 'at'), J(H2_BACK), NOP]  # displaced originals
    # ---- H3: reset -> TAG++ (separate blob at H3_VA) ----
    w3 = [lui('t8', ghi), lhu('t9', glo, 't8'), addiu('t9', 't9', 1), sh('t9', glo, 't8'),
          lui('at', 0x47), lh('a0', -7364, 'at'), J(H3_BACK), NOP]   # displaced originals
    return w, h1, h2, w3


def foff(va):
    if va >= CAVE_VA: return CAVE_FILE + (va - CAVE_VA)
    return FOFF + (va - VBASE)


def main():
    iso = sys.argv[1]; write = "--write" in sys.argv; revert = "--revert" in sys.argv
    words, h1, h2, w3 = build()
    blob = b"".join(struct.pack("<I", x) for x in words)
    blob3 = b"".join(struct.pack("<I", x) for x in w3)
    assert CODE_VA + len(blob) <= TABLE_VA, "code overlaps table (%d B)" % len(blob)
    assert H3_VA + len(blob3) <= 0x78C3F8, "H3 overlaps FLAG"
    sites = ((H1, (lui('at', 0x7000), lw('v1', 0, 'at')), CODE_VA + 4 * h1),
             (H2, (lui('at', 0x7000), lh('v0', 0x2C, 'at')), CODE_VA + 4 * h2),
             (H3, (lui('at', 0x47), lh('a0', -7364, 'at')), H3_VA))
    with open(iso, "r+b" if write else "rb") as f:
        base = ELF_LBA * SECTOR
        f.seek(base + 0x1C); phoff = struct.unpack("<I", f.read(4))[0]
        f.seek(base + 0x2A); phsz, phnum = struct.unpack("<HH", f.read(4))
        f.seek(base + phoff + 208 * phsz); t, off, va, pa, fsz, msz = struct.unpack("<IIIIII", f.read(24))
        assert off == CAVE_FILE and va == CAVE_VA
        print("cave segment ends 0x%X, need 0x%X -> %s" % (va + fsz, SEG_END, "ok" if va + fsz >= SEG_END else "GROW FIRST"))
        if va + fsz < SEG_END: return 1
        states = []
        for site, orig, cave in sites:
            f.seek(base + foff(site)); cur = struct.unpack("<II", f.read(8))
            o = struct.pack("<II", *orig); p = struct.pack("<II", J(cave), NOP)
            st = "original" if struct.pack("<II", *cur) == o else "patched" if struct.pack("<II", *cur) == p else "UNKNOWN %08x %08x" % cur
            states.append(st); print("site 0x%X: %s" % (site, st))
        if any(s.startswith("UNKNOWN") for s in states): return 1
        print("code %d words at 0x%X, table 0x%X..0x%X, tag 0x%X" % (len(words), CODE_VA, TABLE_VA, TABLE_VA + 1024, TAG_VA))
        if not write:
            print("(dry run)"); return 0
        if revert:
            for site, orig, cave in sites:
                f.seek(base + foff(site)); f.write(struct.pack("<II", *orig))
            f.seek(base + foff(CODE_VA)); f.write(b"\x00" * (SEG_END - CODE_VA))
            f.seek(base + foff(H3_VA)); f.write(b"\x00" * len(blob3))
            f.seek(base + foff(TAG_VA)); f.write(b"\x00\x00")
            print("reverted"); return 0
        f.seek(base + foff(CODE_VA)); f.write(b"\x00" * (SEG_END - CODE_VA))
        f.seek(base + foff(CODE_VA)); f.write(blob)
        f.seek(base + foff(H3_VA)); f.write(blob3)
        f.seek(base + foff(TAG_VA)); f.write(b"\x01\x00")            # TAG starts at 1 (table zero => never matches)
        for site, orig, cave in sites:
            f.seek(base + foff(site)); f.write(struct.pack("<II", J(cave), NOP))
        f.flush()
        ok = True
        f.seek(base + foff(CODE_VA)); ok &= f.read(len(blob)) == blob
        for site, orig, cave in sites:
            f.seek(base + foff(site)); ok &= f.read(8) == struct.pack("<II", J(cave), NOP)
        print("written; read-back %s" % ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
