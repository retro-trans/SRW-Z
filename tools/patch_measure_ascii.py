# -*- coding: utf-8 -*-
"""Make the UI string-width measure (0x139B00) count half-width glyphs PER GLYPH.

0x139B00 is what the menu/popup layer uses to place text that FOLLOWS other
text on the same line (append draw 0x3582A0 -> 0x139B00) and to centre lines
(layout 0x359600). It walks the string TWO BYTES per character (Shift-JIS) and
adds the full-width advance (22) per pair. Our menu text is 1-byte ASCII drawn
PROPORTIONALLY (blit advance hook 0x78BA60: table[idx]+1 from the 69-byte table
at 0x78B960, bold +2, space 13), so:

  * every pair of ASCII letters was measured as one 22 char instead of two
    ~10px glyphs -> the following text started inside the name
    (Bazaar: 「Nanoskin Armo|will be bought.", "unequipped2)", "Custom200");
  * an odd-length string puts its NUL in the second byte of a pair; the loop
    only tests the first byte, so it ran on past the terminator into whatever
    the scratch buffer held before -> the same item laid out differently
    depending on the previous popup.

v1 (0.9.57) added a flat 13 per glyph: consistent, but a gap growing with the
name (~30%) showed menus are proportional. v2 mirrors the blit hook exactly.

Hook at the loop head 0x139B78 -> cave 0x78C210:
  ASCII 0x20..0x7E (except the 0x2E..0x3D control range and <0x20, which take
  the original path): consume ONE byte, v0 += MAP[c-0x20]  (MAP at 0x78C300,
  96 bytes built here from the live table: mapped glyphs table[idx]+1, space
  and unmapped 13).
  Private codes 0x8540..0x85C9: idx = code-0x8540; 0x8585 -> 12; idx<69 ->
  table[idx]+1; else table[idx-69]+2.  Everything else: original path.
A NUL is always seen at the loop head, so no overrun.

Cave segment must be grown first (grow_cave.py --bytes 512 -> end 0x78C408).
Registers: at/t4/t8 are loop temporaries in 0x139B00 (recomputed each pass);
v1 holds a live constant and is NOT touched.

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
CAVE = 0x78C210
TABLE_VA = 0x78B960      # 69-byte per-glyph advance table (patch_vwf_widths)
MAP_VA = 0x78C300        # 96-byte ASCII (0x20..0x7F) -> advance map
HW_ORDER = ([0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A))
            + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)))   # patch_hwfont HW_MAP order

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


def I(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)
def SPC(rs, rt, rd, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | fn
def J(target): return (0x02 << 26) | ((target >> 2) & 0x3FFFFFF)
def lbu(rt, off, rs): return I(0x24, rs, rt, off)
def addiu(rt, rs, imm): return I(0x09, rs, rt, imm)
def sltiu(rt, rs, imm): return I(0x0B, rs, rt, imm)
def andi(rt, rs, imm): return I(0x0C, rs, rt, imm)
def ori(rt, rs, imm): return I(0x0D, rs, rt, imm)
def lui(rt, imm): return I(0x0F, 'zero', rt, imm)
def beq(rs, rt, off): return I(0x04, rs, rt, off)
def bne(rs, rt, off): return I(0x05, rs, rt, off)
def addu(rd, rs, rt): return SPC(rs, rt, rd, 0x21)
NOP = 0


def build():
    w = []
    def fix(idx, target): w[idx] = (w[idx] & 0xFFFF0000) | ((target - (idx + 1)) & 0xFFFF)
    LOOP = 0
    w.append(lbu('t3', 0, 'a0'))                       # 0 LOOP
    w.append(bne('t3', 'zero', 2))                     # 1 -> 4
    w.append(NOP)                                      # 2
    w.append(J(END))                                   # 3 string ended
    w.append(NOP)                                      # 4
    w.append(sltiu('at', 't3', 0x80))                  # 5
    w.append(beq('at', 'zero', 0))                     # 6 -> TWOBYTE
    w.append(NOP)                                      # 7
    w.append(addiu('at', 't3', -0x2E))                 # 8
    w.append(sltiu('at', 'at', 0x10))                  # 9  0x2E..0x3D control bytes
    w.append(bne('at', 'zero', 0))                     # 10 -> ORIG
    w.append(NOP)                                      # 11
    w.append(sltiu('at', 't3', 0x20))                  # 12 < space
    w.append(bne('at', 'zero', 0))                     # 13 -> ORIG
    w.append(NOP)                                      # 14
    hi = (MAP_VA + 0x8000) >> 16; lo = MAP_VA - (hi << 16)
    w.append(addiu('at', 't3', -0x20))                 # 15
    w.append(lui('t4', hi))                            # 16
    w.append(addu('t4', 't4', 'at'))                   # 17
    w.append(lbu('t4', lo, 't4'))                      # 18  adv = MAP[c-0x20]
    w.append(addiu('a0', 'a0', 1))                     # 19
    w.append(beq('zero', 'zero', 0))                   # 20 -> LOOP
    w.append(addu('v0', 'v0', 't4'))                   # 21 (delay)
    TW = len(w)                                        # TWOBYTE:
    w.append(addiu('at', 't3', -0x85))                 # 22
    w.append(bne('at', 'zero', 0))                     # 23 -> ORIG
    w.append(NOP)                                      # 24
    w.append(lbu('t4', 1, 'a0'))                       # 25
    w.append(addiu('at', 't4', -0x40))                 # 26  idx = trail-0x40 = code-0x8540
    w.append(sltiu('t8', 'at', 0x8A))                  # 27
    w.append(beq('t8', 'zero', 0))                     # 28 -> ORIG (not private range)
    w.append(NOP)                                      # 29
    w.append(addiu('t8', 'at', -69))                   # 30  t8 = idx-69
    w.append(bne('t8', 'zero', 2))                     # 31  idx==69 (0x8585)?  no -> 34
    w.append(NOP)                                      # 32
    w.append(beq('zero', 'zero', 0))                   # 33 -> ADD
    w.append(ori('t4', 'zero', 12))                    # 34 (delay) adv = 12   [also fallthrough target]
    w.append(sltiu('t4', 'at', 69))                    # 35  t4 = 1 if regular
    w.append(bne('t4', 'zero', 2))                     # 36  regular -> 39
    w.append(ori('t4', 'zero', 1))                     # 37  (delay) +1
    w.append(addiu('at', 'at', -69))                   # 38  bold: idx-69
    w.append(ori('t4', 'zero', 2))                     # 39  +2  <- regular lands here?? (see fix below)
    thi = (TABLE_VA + 0x8000) >> 16; tlo = TABLE_VA - (thi << 16)
    w.append(lui('t8', thi))                           # 40
    w.append(addu('t8', 't8', 'at'))                   # 41
    w.append(lbu('t8', tlo, 't8'))                     # 42  table[idx]
    w.append(addu('t4', 't4', 't8'))                   # 43  adv = table + 1|2
    ADD = len(w)                                       # ADD:
    w.append(addiu('a0', 'a0', 2))                     # 44
    w.append(beq('zero', 'zero', 0))                   # 45 -> LOOP
    w.append(addu('v0', 'v0', 't4'))                   # 46 (delay)
    ORIGI = len(w)                                     # ORIG:
    w.append(andi('t4', 't3', 0xFFFF))                 # 47
    w.append(J(RESUME))                                # 48
    w.append(NOP)                                      # 49
    # branch 36 must skip BOTH bold instructions (38, 39): regular -> 40
    w[36] = bne('t4', 'zero', 3)
    # 31: when idx != 69 skip the ADD12 pair (33,34) -> 35
    w[31] = bne('t8', 'zero', 3)
    fix(6, TW); fix(10, ORIGI); fix(13, ORIGI); fix(20, LOOP); fix(23, ORIGI); fix(28, ORIGI)
    fix(33, ADD); fix(45, LOOP)
    return w


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
    words = build()
    blob = b"".join(struct.pack("<I", x) for x in words)
    assert CAVE + len(blob) <= MAP_VA, "cave code runs into the map"
    with open(iso, "r+b" if write else "rb") as f:
        base = ELF_LBA * SECTOR
        f.seek(base + 0x1C); phoff = struct.unpack("<I", f.read(4))[0]
        f.seek(base + 0x2A); phsz, phnum = struct.unpack("<HH", f.read(4))
        f.seek(base + phoff + 208 * phsz); t, off, va, pa, fsz, msz = struct.unpack("<IIIIII", f.read(24))
        assert off == CAVE_FILE and va == CAVE_VA, "cave phdr moved"
        need = foff(MAP_VA) + 96 - CAVE_FILE
        print("cave segment filesz 0x%X, need 0x%X -> %s" % (fsz, need, "ok" if fsz >= need else "GROW FIRST"))
        if fsz < need: return 1
        f.seek(base + foff(HOOK)); cur = f.read(8)
        orig = struct.pack("<II", lbu('t3', 0, 'a0'), beq('t3', 'zero', (END - (HOOK2 + 4)) // 4))
        patched = struct.pack("<II", J(CAVE), NOP)
        state = "original" if cur == orig else "patched" if cur == patched else "UNKNOWN %s" % cur.hex()
        print("hook site 0x%X: %s" % (HOOK, state))
        f.seek(base + foff(TABLE_VA)); table = f.read(69)
        m = build_map(table)
        print("map: space=%d P=%d s=%d l=%d A=%d 0=%d (=%d" % (m[0], m[ord('P') - 32], m[ord('s') - 32], m[ord('l') - 32], m[ord('A') - 32], m[ord('0') - 32], m[ord('(') - 32]))
        if not write:
            print("(dry run) %d cave words" % len(words)); return 0
        if revert:
            f.seek(base + foff(HOOK)); f.write(orig)
            f.seek(base + foff(CAVE)); f.write(b"\x00" * (MAP_VA + 96 - CAVE))
            print("reverted"); return 0
        assert state in ("original", "patched"), state
        f.seek(base + foff(CAVE)); f.write(blob + b"\x00" * (MAP_VA - CAVE - len(blob)))
        f.seek(base + foff(MAP_VA)); f.write(m)
        f.seek(base + foff(HOOK)); f.write(patched)
        f.flush()
        f.seek(base + foff(HOOK)); ok1 = f.read(8) == patched
        f.seek(base + foff(CAVE)); ok2 = f.read(len(blob)) == blob
        f.seek(base + foff(MAP_VA)); ok3 = f.read(96) == m
        print("written; read-back hook %s cave %s map %s" % (ok1, ok2, ok3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
