# -*- coding: utf-8 -*-
"""PERMANENT terrain micro-glyphs: AIR / GND / SEA / SPC / WTR.

The terrain kanji 空陸海宇水 are font-rendered, so neither texture
replacement nor a string patch can reach them. This stamps custom art
into their MASTER-FONT cells at draw time, the same idea patch_hwfont
uses for the half-width Latin set, but for arbitrary (scattered) kanji
codes instead of the contiguous private range.

Mechanism - a trampoline on BHOOK (the per-glyph blit hook):
  BHOOK+0 becomes   j TERR      (BHOOK+4 -> nop)
  TERR: if the pending glyph code is one of the five, copy 288 bytes of
        raw 4bpp art into that code's master-font cell, then re-execute
        BHOOK's two displaced instructions and jump back to BHOOK+8.
  cell = *(u32*)0x46E3A8 + ((lead-0x81)*192 + (trail-0x40)) * 288
No registers besides t0-t7 are touched and no jal is used, so BHOOK's
own ra/arg state is untouched.

Art is RAW 4bpp (288 B/glyph, 12 B/row, low nibble = even x) so the
copier is a plain 72-word loop - no bit expansion, minimal code.
The cave PT_LOAD is grown into the ELF's unused tail (0x34F450..0x34F908)
to hold art + code.

Usage: patch_terrain_glyphs.py <iso> [--revert]   (idempotent)
"""
import struct
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

from PIL import Image, ImageDraw, ImageFont
from patch_hwfont import Asm

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80
CAVE = 0x78A070
BHOOK = CAVE + 0x210
FONTPTR = 0x0046E3A8
CELL_BYTES = 288

# 0x78B920..0x78BBA0 and 0x78BBA0..0x78BCC8 are the CAPTION PAGING caves -
# art/code go AFTER them, in the space opened by growing the segment.
ROW0, NROWS = 8, 14               # micro words only ink rows 8..21
GBYTES = NROWS * 12               # 168 B per glyph
ART_VA = CAVE + 0x1C60            # 0x78BCD0: clear of both caption caves
TABLE_VA = ART_VA + 5 * GBYTES    # 5 * 4 B cell offsets
CODE_VA = TABLE_VA + 0x20
NEW_FSZ = 0x2198                  # grown into the ELF tail (max without resize)

FONT = r"C:\Windows\Fonts\arialbd.ttf"
WORDS = [("\u7a7a", "AIR"), ("\u9678", "GND"), ("\u6d77", "SEA"),
         ("\u5b87", "SPC"), ("\u6c34", "WTR")]
SIZE = 13


def cell_index(ch):
    b = ch.encode("cp932")
    return (b[0] - 0x81) * 192 + (b[1] - 0x40)


def render_cell(word, px_h=SIZE):
    """24x24 raw 4bpp cell bytes (12 B/row, low nibble = even x)."""
    K = 4
    img = Image.new("L", (24 * K, 24 * K), 0)
    dr = ImageDraw.Draw(img)
    pt = px_h * K
    while pt > 4:
        font = ImageFont.truetype(FONT, pt)
        bb = dr.textbbox((0, 0), word, font=font)
        if bb[2] - bb[0] <= 22 * K:
            break
        pt -= 2
    bb = dr.textbbox((0, 0), word, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    dr.text(((23 * K) - tw - bb[0], (21 * K) - th - bb[1]), word,
            font=font, fill=255)
    small = img.resize((24, 24), Image.LANCZOS)
    p = small.load()
    out = bytearray(CELL_BYTES)
    for row in range(24):
        for col in range(24):
            v = p[col, row]
            lv = 15 if v >= 150 else 10 if v >= 90 else 5 if v >= 40 else 0
            if not lv:
                continue
            o = row * 12 + col // 2
            out[o] = (out[o] & 0xF0) | lv if col % 2 == 0 else \
                     (out[o] & 0x0F) | (lv << 4)
    for row in list(range(0, ROW0)) + list(range(ROW0 + NROWS, 24)):
        assert not any(out[row * 12:(row + 1) * 12]), \
            "%r inks row %d - widen ROW0/NROWS" % (word, row)
    return bytes(out[ROW0 * 12:(ROW0 + NROWS) * 12])


def build_terr():
    a = Asm(CODE_VA)
    a.lui("t1", 0x7000)
    a.lhu("t0", 0x60, "t1")                  # pending glyph code
    for i, (ch, _w) in enumerate(WORDS):
        code = struct.unpack(">H", ch.encode("cp932"))[0]
        a.ori("t1", "zero", code)
        a.beq("t0", "t1", "hit%d" % i)
        a.nop()
    a.j(BHOOK + 8)                           # no match: straight back
    a.nop()
    for i, (ch, _w) in enumerate(WORDS):
        a.label("hit%d" % i)
        a.ori("t2", "zero", i)               # art index
        a.j(CODE_VA + 0)                     # placeholder, fixed below
        a.nop()
    # (the per-hit jumps are rewritten to 'copy' once its address is known)
    a.label("copy")
    a.lui("t4", (FONTPTR + 0x8000) >> 16)
    a.lw("t4", FONTPTR - (((FONTPTR + 0x8000) >> 16) << 16), "t4")
    a.beqz("t4", "done")
    a.nop()
    a.lui("t3", TABLE_VA >> 16)
    a.ori("t3", "t3", TABLE_VA & 0xFFFF)
    a.sll("t5", "t2", 2)
    a.addu("t3", "t3", "t5")
    a.lw("t3", 0, "t3")                      # cell byte offset
    a.addu("t8", "t4", "t3")                 # cell base
    # blank the whole 288-byte cell first
    a.addu("t4", "t8", "zero")
    a.ori("t6", "zero", CELL_BYTES // 4)
    a.label("zloop")
    a.sw("zero", 0, "t4")
    a.addiu("t4", "t4", 4)
    a.addiu("t6", "t6", -1)
    a.bnez("t6", "zloop")
    a.nop()
    # copy the 14 inked rows into place (row ROW0 -> byte ROW0*12)
    a.sll("t5", "t2", 7)                     # *128
    a.sll("t7", "t2", 5)                     # *32
    a.addu("t5", "t5", "t7")
    a.sll("t7", "t2", 3)                     # *8   => *168
    a.addu("t5", "t5", "t7")
    a.lui("t7", ART_VA >> 16)
    a.ori("t7", "t7", ART_VA & 0xFFFF)
    a.addu("t5", "t7", "t5")                 # src
    a.addiu("t4", "t8", ROW0 * 12)           # dest
    a.ori("t6", "zero", GBYTES // 4)
    a.label("loop")
    a.lw("t7", 0, "t5")
    a.sw("t7", 0, "t4")
    a.addiu("t5", "t5", 4)
    a.addiu("t4", "t4", 4)
    a.addiu("t6", "t6", -1)
    a.bnez("t6", "loop")
    a.nop()
    a.label("done")
    a.lui("t1", 0x7000)                      # displaced BHOOK+0
    a.j(BHOOK + 8)
    a.lhu("t0", 0x60, "t1")                  # displaced BHOOK+4 (delay slot)
    return a


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    iso = open(iso_path, "r+b")
    iso.seek(ELF_LBA * SECTOR)
    elf = bytearray(iso.read(3471624))

    def put(va, blob):
        if va >= CAVE:
            off = 0x34D770 + (va - CAVE)
        else:
            off = va - VBASE + FOFF
        elf[off:off + len(blob)] = blob

    def get(va, n):
        off = 0x34D770 + (va - CAVE) if va >= CAVE else va - VBASE + FOFF
        return bytes(elf[off:off + n])

    if revert:
        a = Asm(BHOOK)
        a.lui("t1", 0x7000)
        a.lhu("t0", 0x60, "t1")
        put(BHOOK, a.bytes_())
        print("BHOOK trampoline removed (art left in place, harmless)")
    else:
        # 1) art + cell-offset table
        art = b"".join(render_cell(w) for _ch, w in WORDS)
        assert len(art) == 5 * GBYTES, len(art)
        table = b"".join(struct.pack("<I", cell_index(ch) * CELL_BYTES)
                         for ch, _w in WORDS)
        put(ART_VA, art)
        put(TABLE_VA, table)
        # 2) code (two passes: 'copy' address is known after the first build)
        a = build_terr()
        copy_va = a.labels["copy"]
        code = bytearray(a.bytes_())
        for i in range(len(WORDS)):
            hit = a.labels["hit%d" % i] - CODE_VA
            struct.pack_into("<I", code, hit + 4,
                             (2 << 26) | ((copy_va >> 2) & 0x03FFFFFF))
        assert CODE_VA + len(code) <= CAVE + NEW_FSZ, len(code)
        put(CODE_VA, bytes(code))
        # 3) BHOOK trampoline
        t = Asm(BHOOK)
        t.j(CODE_VA)
        t.nop()
        put(BHOOK, t.bytes_())
        print("art %d B at %#x, code %d B at %#x, trampoline at %#x"
              % (len(art) + len(table), ART_VA, len(code), CODE_VA, BHOOK))

    # 4) grow the cave PT_LOAD
    phoff = struct.unpack_from("<I", elf, 28)[0]
    phnum = struct.unpack_from("<H", elf, 44)[0]
    ent = struct.unpack_from("<H", elf, 42)[0]
    for k in range(phnum):
        o = phoff + k * ent
        t, off, va, pa, fsz, msz, fl, al = struct.unpack_from("<8I", elf, o)
        if va == CAVE:
            if fsz < NEW_FSZ:
                struct.pack_into("<II", elf, o + 16, NEW_FSZ, NEW_FSZ)
                print("cave PT_LOAD grown %#x -> %#x" % (fsz, NEW_FSZ))
            break
    iso.seek(ELF_LBA * SECTOR)
    iso.write(bytes(elf))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
