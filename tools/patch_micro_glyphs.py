# -*- coding: utf-8 -*-
"""MICRO-GLYPHS: kanji cells re-drawn as Latin art, at the kanji's own width.

Supersedes patch_terrain_glyphs.py and covers two families:

  TERRAIN  空陸海宇水 -> AIR GND SEA SPC WTR   (3 letters, custom art)
  SPIRITS  熱魂閃不鉄集必加迅覚手狙直幸努乱分
           -> Va So Al Re Wa Fo St Ac Sw Aw Me Sn Di Lu Ga Co An
           (2 letters, COMPOSED from the half-width atlas at run time)

Why composed: a spirit pair is exactly two 12 px atlas glyphs and a kanji
cell is exactly 24 px, so the pair needs no art of its own - just two
atlas indices. 17 glyphs of stored art would need ~2.9 KB; the cave has
180 B free. Two indices need 8.

Why cells and not a string patch: 0.8.41 replaced the strip STRING with
"VaSoAl..." and it drifted - the game paints the pilot's own spirits in
white OVER the gray list on a fixed 24 px pitch, which only a full-width
cell can match. (It also ran off the panel: two half-width advances are
26 px, not 24.)

Everything is stored 2bpp (levels x5 -> 0/5/10/15), the format the atlas
already uses, so terrain art costs 84 B instead of 168 B and a single
expansion loop serves both families.

  ART   0x78BCD0  5 x 84 B   terrain, as two 12 px column halves
  TABLE 0x78BE80  22 x 8 B   [code u16][nrows u8][row0 u8][loff u16][roff u16]
                             loff/roff are offsets from ATLAS_VA
  CODE  0x78BF40  reached by the BHOOK trampoline (j GLYF / nop)

Usage: patch_micro_glyphs.py <iso> [--revert]   (idempotent)
"""
import struct
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

from patch_hwfont import Asm, HW_MAP, ATLAS_VA
from patch_terrain_glyphs import render_cell

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80
CAVE = 0x78A070
BHOOK = CAVE + 0x210
FONTPTR = 0x0046E3A8
NEW_FSZ = 0x2198

ART_VA = 0x78BCD0                 # clear of both caption paging caves
TABLE_VA = 0x78BE80
CODE_VA = 0x78BF40
CAVE_END = CAVE + NEW_FSZ         # 0x78C208

TERRAIN = [("\u7a7a", "AIR"), ("\u9678", "GND"), ("\u6d77", "SEA"),
           ("\u5b87", "SPC"), ("\u6c34", "WTR")]
TROW0, TNROWS = 8, 14

# Spirits do NOT reuse their kanji code: the tutorial bank still writes
# 加/手/分/必/集/直/不 in ordinary Japanese sentences (359 hits), and a
# master-font cell is global, so stamping the kanji itself would turn that
# text into "AcMeAn...".  Instead each spirit gets a PRIVATE code in SJIS
# lead row 0x85, which is fully unassigned - the same trick patch_hwfont
# uses for the half-width set (0x8540..0x85C9, so we start right after at
# 0x85CA; codes past that range are NOT flagged half-width, so they render
# as a normal 24 px full-width cell).  patch_spirit_abbrev.py rewrites the
# strip and the record slots to these codes.
PRIV_BASE = 0x85CA

# each spirit's own English name in this ELF, cut to two letters
SPIRITS = [
    ("\u71b1", "Va"), ("\u9b42", "So"), ("\u9583", "Al"), ("\u4e0d", "Re"),
    ("\u9244", "Wa"), ("\u96c6", "Fo"), ("\u5fc5", "St"), ("\u52a0", "Ac"),
    ("\u8fc5", "Sw"), ("\u899a", "Aw"), ("\u624b", "Me"), ("\u72d9", "Sn"),
    ("\u76f4", "Di"), ("\u5e78", "Lu"), ("\u52aa", "Ga"), ("\u4e71", "Co"),
    ("\u5206", "An"),
]
# One more private cell: a BLANK.  The white "spirits this pilot has" string
# is built by 0x35E370, which pads every unowned slot with a full-width space
# (0x8140) and inserts one more as the "/" separator (format at 0x442648) -
# and patch_hwfont deliberately advances 0x8140 by 13 px, because that space
# IS the English word space.  A full-width cell advances by the engine's own
# constant (*(s16*)0x70000038), so the white string walked left of the gray
# one, landing "Fo" on top of "Wa".  Masking with a blank CELL puts both
# strings on the identical advance path.
BLANK_CODE = PRIV_BASE + len(SPIRITS)     # 0x85DB
BLANK_VA = 0x78C110                       # cave spare, past the code
BLANK_BYTES = 72                          # 24 rows x 3 B of zeros

GLYPH_BYTES = 72                  # atlas glyph: 24 rows x 3 B (12 px, 2bpp)
ASCII_IDX = {c: g - 0x8540 for c, g in HW_MAP}


def code_of(ch):
    return struct.unpack(">H", ch.encode("cp932"))[0]


def art_2bpp_halves(word):
    """render_cell gives 4bpp rows (12 B); split into two 12 px 2bpp halves."""
    raw = render_cell(word)                       # TNROWS * 12 bytes
    left, right = bytearray(), bytearray()
    for r in range(TNROWS):
        row = raw[r * 12:(r + 1) * 12]
        for half, out in ((0, left), (6, right)):
            acc = 0
            for k in range(6):                    # 6 bytes = 12 pixels
                b = row[half + k]
                for nib in (b & 0x0F, b >> 4):    # even x first
                    assert nib in (0, 5, 10, 15), nib
                    acc = (acc << 2) | (nib // 5)
            out += acc.to_bytes(3, "big")
    assert len(left) == len(right) == TNROWS * 3
    return bytes(left) + bytes(right)


def expand_half(a, dst_bias, tag):
    """12 px of the row word in t0 -> 6 bytes at t4+dst_bias (2bpp -> 4bpp)"""
    a.ori("t8", "zero", 22)                       # MSB-first bit position
    a.ori("t7", "zero", 0)                        # output byte counter
    a.label(tag)
    a.srlv("t2", "t0", "t8")
    a.andi("t2", "t2", 3)
    a.sll("t9", "t2", 2)
    a.addu("t2", "t9", "t2")                      # even x -> low nibble, v*5
    a.addiu("t8", "t8", -2)
    a.srlv("t9", "t0", "t8")
    a.andi("t9", "t9", 3)
    a.sll("t1", "t9", 2)
    a.addu("t9", "t1", "t9")
    a.sll("t9", "t9", 4)                          # odd x -> high nibble
    a.or_("t2", "t2", "t9")
    a.addu("t1", "t4", "t7")
    if dst_bias:
        a.addiu("t1", "t1", dst_bias)
    a.sb("t2", 0, "t1")
    a.addiu("t7", "t7", 1)
    a.addiu("t8", "t8", -2)
    a.sltiu("t1", "t7", 6)
    a.bnez("t1", tag)
    a.nop()


def load_row(a, src):
    """3 bytes at src -> t0, a 24-bit MSB-first row of 12 2bpp pixels"""
    a.lbu("t1", 0, src)
    a.sll("t1", "t1", 16)
    a.lbu("t2", 1, src)
    a.sll("t2", "t2", 8)
    a.or_("t1", "t1", "t2")
    a.lbu("t2", 2, src)
    a.or_("t0", "t1", "t2")


def build_rows():
    """[(code, nrows, row0, loff, roff)] - terrain art then spirit pairs"""
    rows = []
    for i, (ch, _w) in enumerate(TERRAIN):
        base = (ART_VA - ATLAS_VA) + i * TNROWS * 6
        rows.append((code_of(ch), TNROWS, TROW0, base, base + TNROWS * 3))
    for i, (ch, pair) in enumerate(SPIRITS):
        l, r = (ASCII_IDX[ord(c)] * GLYPH_BYTES for c in pair)
        rows.append((PRIV_BASE + i, 24, 0, l, r))
    blank = BLANK_VA - ATLAS_VA
    rows.append((BLANK_CODE, 24, 0, blank, blank))
    return rows


def build_code(nent):
    a = Asm(CODE_VA)
    a.lui("t1", 0x7000)
    a.lhu("t0", 0x60, "t1")                       # pending glyph code
    a.lui("t3", TABLE_VA >> 16)
    a.ori("t3", "t3", TABLE_VA & 0xFFFF)
    a.ori("t6", "zero", nent)
    a.label("scan")
    a.lhu("t1", 0, "t3")
    a.beq("t0", "t1", "found")
    a.nop()
    a.addiu("t3", "t3", 8)
    a.addiu("t6", "t6", -1)
    a.bnez("t6", "scan")
    a.nop()
    a.j(0)                                        # -> 'done', fixed up below
    a.nop()
    a.label("found")
    a.lui("t4", (FONTPTR + 0x8000) >> 16)
    a.lw("t4", FONTPTR - (((FONTPTR + 0x8000) >> 16) << 16), "t4")
    a.beqz("t4", "done")
    a.nop()
    # cell = font + ((lead-0x81)*192 + (trail-0x40)) * 288
    a.srl("t1", "t0", 8)
    a.andi("t2", "t0", 0xFF)
    a.addiu("t1", "t1", -0x81)
    a.addiu("t2", "t2", -0x40)
    a.ori("t9", "zero", 192)
    a.mult("t1", "t9")
    a.mflo("t1")
    a.addu("t1", "t1", "t2")
    a.ori("t9", "zero", 288)
    a.mult("t1", "t9")
    a.mflo("t1")
    a.addu("t8", "t4", "t1")                      # cell base
    # blank the cell so none of the kanji ink survives underneath
    a.addu("t4", "t8", "zero")
    a.ori("t6", "zero", 288 // 4)
    a.label("zloop")
    a.sw("zero", 0, "t4")
    a.addiu("t4", "t4", 4)
    a.addiu("t6", "t6", -1)
    a.bnez("t6", "zloop")
    a.nop()
    # both source pointers, then the first destination row
    a.lui("t9", ATLAS_VA >> 16)
    a.ori("t9", "t9", ATLAS_VA & 0xFFFF)
    a.lhu("t5", 4, "t3")
    a.addu("t5", "t9", "t5")                      # left source
    a.lhu("t1", 6, "t3")
    a.addu("t9", "t9", "t1")                      # right source
    a.lbu("t2", 3, "t3")                          # row0
    a.sll("t1", "t2", 3)
    a.sll("t4", "t2", 2)
    a.addu("t1", "t1", "t4")                      # row0 * 12
    a.lbu("t6", 2, "t3")                          # nrows
    a.addu("t4", "t8", "t1")                      # destination row
    a.addu("t3", "t9", "zero")                    # t3 is now the right source
    a.label("row")
    load_row(a, "t5")
    expand_half(a, 0, "xpl")
    load_row(a, "t3")
    expand_half(a, 6, "xpr")
    a.addiu("t5", "t5", 3)
    a.addiu("t3", "t3", 3)
    a.addiu("t4", "t4", 12)
    a.addiu("t6", "t6", -1)
    a.bnez("t6", "row")
    a.nop()
    a.label("done")
    a.lui("t1", 0x7000)                           # displaced BHOOK+0
    a.j(BHOOK + 8)
    a.lhu("t0", 0x60, "t1")                       # displaced BHOOK+4 (delay)
    return a


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    iso = open(iso_path, "r+b")
    iso.seek(ELF_LBA * SECTOR)
    elf = bytearray(iso.read(3471624))

    def put(va, blob):
        off = 0x34D770 + (va - CAVE) if va >= CAVE else va - VBASE + FOFF
        elf[off:off + len(blob)] = blob

    if revert:
        a = Asm(BHOOK)
        a.lui("t1", 0x7000)
        a.lhu("t0", 0x60, "t1")
        put(BHOOK, a.bytes_())
        print("BHOOK trampoline removed (art/code left, unreferenced)")
    else:
        # 1) terrain art, 2bpp, as left/right column halves
        art = b"".join(art_2bpp_halves(w) for _c, w in TERRAIN)
        assert len(art) == len(TERRAIN) * TNROWS * 6, len(art)
        assert ART_VA + len(art) <= TABLE_VA, "art overruns the table"
        put(ART_VA, art)
        assert BLANK_VA + BLANK_BYTES <= CAVE_END, "blank art overruns the cave"
        put(BLANK_VA, bytes(BLANK_BYTES))
        # 2) one table for both families
        rows = build_rows()
        table = b"".join(struct.pack("<HBBHH", *r) for r in rows)
        assert TABLE_VA + len(table) <= CODE_VA, "table overruns the code"
        put(TABLE_VA, table)
        # 3) code (two passes: 'done' is only known after the first build)
        a = build_code(len(rows))
        code = bytearray(a.bytes_())
        miss = (a.labels["found"] - CODE_VA) // 4 - 2      # the j placeholder
        struct.pack_into("<I", code, miss * 4,
                         (2 << 26) | ((a.labels["done"] >> 2) & 0x03FFFFFF))
        assert CODE_VA + len(code) <= CAVE_END, \
            "code overruns the cave by %d B" % (CODE_VA + len(code) - CAVE_END)
        put(CODE_VA, bytes(code))
        # 4) trampoline
        t = Asm(BHOOK)
        t.j(CODE_VA)
        t.nop()
        put(BHOOK, t.bytes_())
        print("art %d B, table %d B (%d glyphs), code %d B, %d B cave spare"
              % (len(art), len(table), len(rows), len(code),
                 CAVE_END - (CODE_VA + len(code))))

    iso.seek(ELF_LBA * SECTOR)
    iso.write(bytes(elf))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
