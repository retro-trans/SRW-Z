# -*- coding: utf-8 -*-
"""Pixel-accurate glossary-link underline (v2 FINAL, companion to patch_linkpos).

The link underline was N fullwidth ＿ (21px units) per term CHAR - wrong length
over 13px VWF English, and its segment end-X leaked into the next text's
position. Fixed with (all live-tuned in-game via PINE, user-approved):

  * NEW GLYPH: half-width underscore, private index 69 (code 0x8585), bitmap
    at its natural table slot 0x78B918. Ink: bottom row only (row 23, 12px
    wide, 1px thick) - sits with a small gap under the letters.
  * DECODER RANGE: `sltiu t9,t1,69` at 0x78A2B4 raised to 70 so index 69 is a
    normal glyph (indexes >=70 remain bold aliases of table[idx-69]; nothing
    emits 0x8585 today - spaces map to 0x8140 - so no collision).
  * ADVANCE HOOK v2 relocated to 0x78BA60 (callsite 0x13AB7C repointed): same
    logic as the cave original at 0x78A4B0 plus one case - code 0x8585
    advances 12 (== ink width) so consecutive underscores connect seamlessly
    (default private advance is destwidth+1 = 13, which left 1px dots).
  * UNDERLINE STUB 0x78B960 (hooked from the copy call at 0x2215F4):
    saves the term's true end-X (0x46E340) to scratch 0x78BA50, computes
    count = round(term_pixel_width / 12) clamped 1..26, redirects the copy
    source to an 0x8585 x26 constant at 0x78BA10.
  * RESTORE STUB 0x78B9E0 (hooked at 0x221628/2C after the underline draw):
    restores the saved term end-X so patch_linkpos places the following text
    at the TERM's end, not the underline's.

Cave PT_LOAD fsz/msz extended 0x18B0 -> 0x1A50 into the ELF's unused file
tail; everything stays below HEAP_BASE 0x78CD00.

Usage: patch_underline.py <src.elf> <dst.elf>
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
CAVE_FILE, CAVE_VA = 0x34D770, 0x78A070
HEAP_BASE = 0x78CD00
NEW_FSZ = 0x1A50                       # covers through the advance hook end

def f(va): return CAVE_FILE + (va - CAVE_VA)
def e(va): return FOFF + (va - VBASE)

GLYPH_VA = 0x78B918                    # table slot 69 = 0x78A5B0 + 69*72
STUB_VA = 0x78B960
RESTORE_VA = 0x78B9E0
CONST_VA = 0x78BA10
SCRATCH_VA = 0x78BA50
ADV_VA = 0x78BA60
COPY_FN = 0x1A1190

STUB = [0x3C010047, 0x8429E340, 0x3C0B0078, 0x356BBA50, 0xA5690000,
        0x01344823, 0x25290006, 0x240A0000, 0x2529FFF4, 0x05200004,
        0x00000000, 0x254A0001, 0x1000FFFB, 0x00000000, 0x15400002,
        0x00000000, 0x240A0001, 0x000A3040, 0x28C10036, 0x14200002,
        0x00000000, 0x24060034, 0x00865821, 0xA1600000, 0xA1600001,
        0x3C050078, 0x34A5BA10,
        (2 << 26) | ((COPY_FN >> 2) & 0x3FFFFFF), 0x00000000]
RESTORE = [0x3C010078, 0x3421BA50, 0x84390000, 0x3C010047, 0xA439E340,
           0x26020002, 0x02429021, 0x03E00008, 0x00000000]
ADV = [0xAFA8FFF0, 0x3C017000, 0x94280060, 0x39018140, 0x1020000B,
       0x00000000, 0x39018585, 0x1020000B, 0x34018540, 0x01010823,
       0x2C21008A, 0x10200008, 0x00000000, 0x9608000C, 0x10000005,
       0x25030001, 0x3403000D, 0x10000002, 0x00000000, 0x3403000C,
       0x00831821, 0x8FA8FFF0, 0x03E00008, 0x3C017000]


def apply(data):
    data = bytearray(data)
    e_phoff = struct.unpack_from("<I", data, 0x1C)[0]
    phnum = struct.unpack_from("<H", data, 0x2C)[0]
    phent = struct.unpack_from("<H", data, 0x2A)[0]
    assert CAVE_VA + NEW_FSZ < HEAP_BASE
    found = False
    for i in range(phnum):
        o = e_phoff + i * phent
        typ, off, va = struct.unpack_from("<III", data, o)
        if typ == 1 and off == CAVE_FILE and va == CAVE_VA:
            struct.pack_into("<II", data, o + 16, NEW_FSZ, NEW_FSZ)
            found = True
    assert found, "cave PT_LOAD not found"
    assert CAVE_FILE + NEW_FSZ <= len(data), "ELF too short for extension"

    # glyph: 72 zero bytes except row 23 (bytes 69..71) solid
    data[f(GLYPH_VA):f(GLYPH_VA) + 72] = b"\x00" * 69 + b"\xFF" * 3
    # decoder normal-range 69 -> 70
    o = f(0x78A2B4)
    cur = struct.unpack_from("<I", data, o)[0]
    assert cur in (0x2D390045, 0x2D390046), hex(cur)
    struct.pack_into("<I", data, o, 0x2D390046)
    # code blocks
    for base, words in ((STUB_VA, STUB), (RESTORE_VA, RESTORE), (ADV_VA, ADV)):
        for i, w in enumerate(words):
            struct.pack_into("<I", data, f(base) + i * 4, w)
    data[f(CONST_VA):f(CONST_VA) + 52] = b"\x85\x85" * 26
    data[f(SCRATCH_VA):f(SCRATCH_VA) + 8] = b"\x00" * 8

    # hooks
    def hook(va, new, ok):
        o = e(va)
        cur = struct.unpack_from("<I", data, o)[0]
        assert cur in ok + (new,), "unexpected %08x at %#x" % (cur, va)
        struct.pack_into("<I", data, o, new)
    jal = lambda t: (3 << 26) | ((t >> 2) & 0x3FFFFFF)
    hook(0x2215F4, jal(STUB_VA), (jal(COPY_FN), 0x0C1E2E48))
    hook(0x221628, jal(RESTORE_VA), (0x26020002,))
    hook(0x22162C, 0x00000000, (0x02429021,))
    hook(0x13AB7C, jal(ADV_VA), (0x0C1E292C,))     # was jal 0x78A4B0
    return bytes(data)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "wb").write(apply(open(src, "rb").read()))
    print("underline v2 patch written:", dst)


if __name__ == "__main__":
    main()
