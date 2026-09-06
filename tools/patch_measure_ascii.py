# -*- coding: utf-8 -*-
"""Popup/menu text placement: measure half-width glyphs per glyph, ONLY where
the popup layout asks (v3).

0x139B00 is the UI string-width measure. It walks the string TWO BYTES per
character (Shift-JIS), adds the full-width 22 per pair, and never tests the
second byte of a pair for NUL. Our menu text is 1-byte ASCII drawn
proportionally (blit advance hook 0x78BA60: table[idx]+1 from the 69-byte table
at 0x78B960, bold +2, space 13). Consequences in the Bazaar buy popup
(three appended segments: 「, name, "' will be bought."):
  * the tail started inside the name (pairs undercount the glyphs);
  * odd-length names ran the scan past the NUL into the previous popup's
    buffer -> layout depended on the previous popup.

History: v1 (0.9.57) hooked the loop globally with a flat 13 -> consistent but
a ~30% gap. v2 (0.9.58) per-glyph widths globally -> the popup text STALLED
part-way ("「Prope"): 0x139B00 has ~120 callers and at least one depends on the
original semantics. v3 therefore leaves every caller alone and enables the
ASCII-aware loop only while a flag is set, and only two sites set it:
    0x35836C  append draw 0x3582A0: x = base + sum(measure(previous items))
    0x3596BC  popup layout 0x359600: per-line width (centering / box width)
Both `jal 0x139B00` are redirected to STUB, which sets FLAG, calls 0x139B00,
clears FLAG (v0/v1 preserved). The loop hook at 0x139B78 -> CAVE reads FLAG:
0 -> original path exactly; 1 -> ASCII 0x20..0x7E consume ONE byte and add
MAP[c-0x20] (MAP built here from the live table), private codes 0x8540..0x85C9
mirror the blit hook (0x8585 -> 12; idx<69 table+1; else table[idx-69]+2).
A NUL is always seen at the loop head, so no overrun.

Cave layout (segment grown by grow_cave.py --bytes 512, ends 0x78C408):
  CAVE 0x78C210 (code, <= 0xE0 B)   MAP 0x78C300 (96 B)
  STUB 0x78C380 (48 B)              FLAG 0x78C3F8 (1 B)
Registers: at/t4/t8 are loop temporaries in 0x139B00; v1 is a live constant
and is NOT touched. STUB clobbers t8/at (dead at both call sites).

Usage: patch_measure_ascii.py <iso> [--write] [--revert]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
CAVE_FILE, CAVE_VA = 0x34D770, 0x78A070
ELF_LBA, SECTOR = 455, 2048
HOOK = 0x139B78          # lbu t3,0(a0)
HOOK2 = 0x139B7C         # beq t3,zero,0x139D08
RESUME = 0x139B84        # after `andi t4,t3,0xFFFF`
END = 0x139D08           # function epilogue (string ended)
MEASURE = 0x139B00
SITES = (0x35836C, 0x3596BC)
CAVE = 0x78C210
MAP_VA = 0x78C300
STUB = 0x78C380
FLAG = 0x78C3F8
TABLE_VA = 0x78B960
HW_ORDER = ([0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A))
            + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)))

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


def I(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)
def SPC(rs, rt, rd, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | fn
def J(target): return (0x02 << 26) | ((target >> 2) & 0x3FFFFFF)
def JAL(target): return (0x03 << 26) | ((target >> 2) & 0x3FFFFFF)
def lbu(rt, off, rs): return I(0x24, rs, rt, off)
def sb(rt, off, rs): return I(0x28, rs, rt, off)
def lw(rt, off, rs): return I(0x23, rs, rt, off)
def sw(rt, off, rs): return I(0x2B, rs, rt, off)
def addiu(rt, rs, imm): return I(0x09, rs, rt, imm)
def sltiu(rt, rs, imm): return I(0x0B, rs, rt, imm)
def andi(rt, rs, imm): return I(0x0C, rs, rt, imm)
def ori(rt, rs, imm): return I(0x0D, rs, rt, imm)
def lui(rt, imm): return I(0x0F, 'zero', rt, imm)
def beq(rs, rt, off): return I(0x04, rs, rt, off)
def bne(rs, rt, off): return I(0x05, rs, rt, off)
def addu(rd, rs, rt): return SPC(rs, rt, rd, 0x21)
def jr(rs): return SPC(rs, 'zero', 'zero', 0x08)
NOP = 0


def hl(va):
    hi = (va + 0x8000) >> 16
    return hi, va - (hi << 16)


def build_cave():
    w = []
    def fix(idx, target): w[idx] = (w[idx] & 0xFFFF0000) | ((target - (idx + 1)) & 0xFFFF)
    fhi, flo = hl(FLAG); mhi, mlo = hl(MAP_VA); thi, tlo = hl(TABLE_VA)
    LOOP = 0
    w.append(lbu('t3', 0, 'a0'))            # 0 LOOP
    w.append(bne('t3', 'zero', 2))          # 1 -> 4
    w.append(NOP)                           # 2
    w.append(J(END))                        # 3 string ended
    w.append(NOP)                           # 4
    w.append(lui('t4', fhi))                # 5
    w.append(lbu('t4', flo, 't4'))          # 6  t4 = FLAG
    w.append(beq('t4', 'zero', 0))          # 7 -> ORIG (flag clear: original semantics)
    w.append(NOP)                           # 8
    w.append(sltiu('at', 't3', 0x80))       # 9
    w.append(beq('at', 'zero', 0))          # 10 -> TWOBYTE
    w.append(NOP)                           # 11
    w.append(addiu('at', 't3', -0x2E))      # 12
    w.append(sltiu('at', 'at', 0x10))       # 13  0x2E..0x3D control bytes
    w.append(bne('at', 'zero', 0))          # 14 -> ORIG
    w.append(NOP)                           # 15
    w.append(sltiu('at', 't3', 0x20))       # 16  < space
    w.append(bne('at', 'zero', 0))          # 17 -> ORIG
    w.append(NOP)                           # 18
    w.append(addiu('at', 't3', -0x20))      # 19
    w.append(lui('t4', mhi))                # 20
    w.append(addu('t4', 't4', 'at'))        # 21
    w.append(lbu('t4', mlo, 't4'))          # 22  adv = MAP[c-0x20]
    w.append(addiu('a0', 'a0', 1))          # 23
    w.append(beq('zero', 'zero', 0))        # 24 -> LOOP
    w.append(addu('v0', 'v0', 't4'))        # 25 (delay)
    TW = len(w)                             # TWOBYTE:
    w.append(addiu('at', 't3', -0x85))      # 26
    w.append(bne('at', 'zero', 0))          # 27 -> ORIG
    w.append(NOP)                           # 28
    w.append(lbu('t4', 1, 'a0'))            # 29
    w.append(addiu('at', 't4', -0x40))      # 30  idx = code-0x8540
    w.append(sltiu('t8', 'at', 0x8A))       # 31
    w.append(beq('t8', 'zero', 0))          # 32 -> ORIG
    w.append(NOP)                           # 33
    w.append(addiu('t8', 'at', -69))        # 34
    w.append(bne('t8', 'zero', 3))          # 35  idx != 69 -> 39
    w.append(NOP)                           # 36
    w.append(beq('zero', 'zero', 0))        # 37 -> ADD  (idx == 69: 0x8585)
    w.append(ori('t4', 'zero', 12))         # 38 (delay) adv = 12
    w.append(sltiu('t4', 'at', 69))         # 39  1 if regular
    w.append(bne('t4', 'zero', 3))          # 40  regular -> 44
    w.append(ori('t4', 'zero', 1))          # 41  (delay) +1
    w.append(addiu('at', 'at', -69))        # 42  bold: idx-69
    w.append(ori('t4', 'zero', 2))          # 43  +2
    w.append(lui('t8', thi))                # 44
    w.append(addu('t8', 't8', 'at'))        # 45
    w.append(lbu('t8', tlo, 't8'))          # 46  table[idx]
    w.append(addu('t4', 't4', 't8'))        # 47
    ADD = len(w)                            # ADD:
    w.append(addiu('a0', 'a0', 2))          # 48
    w.append(beq('zero', 'zero', 0))        # 49 -> LOOP
    w.append(addu('v0', 'v0', 't4'))        # 50 (delay)
    ORIGI = len(w)                          # ORIG:
    w.append(andi('t4', 't3', 0xFFFF))      # 51
    w.append(J(RESUME))                     # 52
    w.append(NOP)                           # 53
    fix(7, ORIGI); fix(10, TW); fix(14, ORIGI); fix(17, ORIGI); fix(24, LOOP)
    fix(27, ORIGI); fix(32, ORIGI); fix(37, ADD); fix(49, LOOP)
    return w


def build_stub():
    fhi, flo = hl(FLAG)
    return [
        addiu('sp', 'sp', -16),
        sw('ra', 0, 'sp'),
        ori('t8', 'zero', 1),
        lui('at', fhi),
        sb('t8', flo, 'at'),        # FLAG = 1
        JAL(MEASURE),
        NOP,
        lui('at', fhi),
        sb('zero', flo, 'at'),      # FLAG = 0
        lw('ra', 0, 'sp'),
        jr('ra'),
        addiu('sp', 'sp', 16),
    ]


def build_map(table):
    m = bytearray([13] * 96)
    for idx, c in enumerate(HW_ORDER):
        m[c - 0x20] = table[idx] + 1
    return bytes(m)


def foff(va):
    if va >= CAVE_VA: return CAVE_FILE + (va - CAVE_VA)
    return FOFF + (va - VBASE)


def main():
    iso = sys.argv[1]; write = "--write" in sys.argv; revert = "--revert" in sys.argv
    cave = b"".join(struct.pack("<I", x) for x in build_cave())
    stub = b"".join(struct.pack("<I", x) for x in build_stub())
    assert CAVE + len(cave) <= MAP_VA and STUB + len(stub) <= FLAG
    with open(iso, "r+b" if write else "rb") as f:
        base = ELF_LBA * SECTOR
        f.seek(base + 0x1C); phoff = struct.unpack("<I", f.read(4))[0]
        f.seek(base + 0x2A); phsz, phnum = struct.unpack("<HH", f.read(4))
        f.seek(base + phoff + 208 * phsz); t, off, va, pa, fsz, msz = struct.unpack("<IIIIII", f.read(24))
        assert off == CAVE_FILE and va == CAVE_VA, "cave phdr moved"
        need = FLAG + 1 - CAVE_VA
        print("cave segment filesz 0x%X, need 0x%X -> %s" % (fsz, need, "ok" if fsz >= need else "GROW FIRST"))
        if fsz < need: return 1
        orig_hook = struct.pack("<II", lbu('t3', 0, 'a0'), beq('t3', 'zero', (END - (HOOK2 + 4)) // 4))
        new_hook = struct.pack("<II", J(CAVE), NOP)
        f.seek(base + foff(HOOK)); cur = f.read(8)
        print("hook 0x%X: %s" % (HOOK, "original" if cur == orig_hook else "patched" if cur == new_hook else "UNKNOWN " + cur.hex()))
        for s in SITES:
            f.seek(base + foff(s)); wv = struct.unpack("<I", f.read(4))[0]
            print("site 0x%X: %s" % (s, "jal measure (original)" if wv == JAL(MEASURE) else "jal stub" if wv == JAL(STUB) else "UNKNOWN %08x" % wv))
        f.seek(base + foff(TABLE_VA)); table = f.read(69)
        m = build_map(table)
        print("map: space=%d P=%d s=%d l=%d A=%d 0=%d" % (m[0], m[ord('P') - 32], m[ord('s') - 32], m[ord('l') - 32], m[ord('A') - 32], m[ord('0') - 32]))
        if not write:
            print("(dry run)"); return 0
        if revert:
            f.seek(base + foff(HOOK)); f.write(orig_hook)
            for s in SITES:
                f.seek(base + foff(s)); f.write(struct.pack("<I", JAL(MEASURE)))
            f.seek(base + foff(CAVE)); f.write(b"\x00" * (FLAG + 1 - CAVE))
            print("reverted"); return 0
        f.seek(base + foff(CAVE)); f.write(b"\x00" * (FLAG + 1 - CAVE))     # clean the whole area first
        f.seek(base + foff(CAVE)); f.write(cave)
        f.seek(base + foff(MAP_VA)); f.write(m)
        f.seek(base + foff(STUB)); f.write(stub)
        f.seek(base + foff(HOOK)); f.write(new_hook)
        for s in SITES:
            f.seek(base + foff(s)); f.write(struct.pack("<I", JAL(STUB)))
        f.flush()
        f.seek(base + foff(CAVE)); ok = f.read(len(cave)) == cave
        f.seek(base + foff(STUB)); ok &= f.read(len(stub)) == stub
        f.seek(base + foff(HOOK)); ok &= f.read(8) == new_hook
        f.seek(base + foff(FLAG)); ok &= f.read(1) == b"\x00"
        print("written; read-back %s" % ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
