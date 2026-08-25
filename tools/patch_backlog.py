# -*- coding: utf-8 -*-
"""Backlog (Triangle) rendering fixes for VWF English text.

ROOT CAUSE (found live via PINE, 2026-08-19): the backlog draws the RAW
record strings (never setText-converted).  The blit consumes bytes 0x2E-0x3D
as CONTROL CODES *before* its on-the-fly ASCII translation, so every raw
'.' (0x2E) acted as a NEWLINE control - each backlog row broke at its first
period and the remainder overprinted the next row.  Digits/':'/';' would
corrupt the same way.

FIXES:
  * CONVCOPY stub (0x78BAF0): a converting copy (ASCII 0x20-0x7E -> private
    2-byte codes via the cave map at 0x78A1BC; SJIS/control bytes pass
    through; NUL-terminates at CONVERTED length).  Hooked over the two
    backlog row-buffer copies at 0x221430/0x221444; the caller's source-length
    NUL writes at 0x22145C/60 are NOPed (they would truncate the grown
    string).  Already-converted text passes through unchanged, so the shared
    dialogue path is unaffected.
  * FLUSH PATH A (0x78BAC0 stub, hook at 0x13AE5C): the VWF dest-width patch
    only covered flush path B (0x13B304); path A still drew private glyphs
    24px wide.  Mirrors the same check (record byte19==0xA7 && destw==12 ->
    12px sprite) using only $at as temp.

Usage: patch_backlog.py <src.elf> <dst.elf>   (apply after patch_underline)
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
CAVE_FILE, CAVE_VA = 0x34D770, 0x78A070
HEAP_BASE = 0x78CD00
NEW_FSZ = 0x1B30                       # through convcopy end 0x78BBA0

def f(va): return CAVE_FILE + (va - CAVE_VA)
def e(va): return FOFF + (va - VBASE)

STUBA_VA = 0x78BAC0
CONV_VA = 0x78BAF0

STUBA = [0x90E10013, 0x382100A7, 0x14200006, 0x250B0017, 0x94E1000C,
         0x3821000C, 0x14200002, 0x00000000, 0x250B000B, 0x0804EB99,
         0x00000000]
CONV = [0x00A04021, 0x00804821, 0x00A65021,
        0x010A082B, 0x10200024, 0x00000000,
        0x910B0000, 0x11600021, 0x00000000,
        0x256CFFE0, 0x2D81005F, 0x1020000C, 0x00000000,
        0x3C0E0078, 0x35CEA1BC, 0x000C6040, 0x01CC7021,
        0x91CF0000, 0x91CC0001, 0xA12F0000, 0xA12C0001,
        0x25290002, 0x1000FFEC, 0x25080001,
        0x256CFF7F, 0x2D81001F, 0x14200008, 0x256CFF20,
        0x2D810010, 0x14200005, 0x00000000,
        0xA12B0000, 0x25290001, 0x1000FFE1, 0x25080001,
        0xA12B0000, 0x910C0001, 0xA12C0001,
        0x25290002, 0x1000FFDB, 0x25080002,
        0xA1200000, 0x03E00008, 0x00000000]


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
            fsz = struct.unpack_from("<I", data, o + 16)[0]
            assert fsz in (0x1A50, NEW_FSZ), hex(fsz)   # after underline v2
            struct.pack_into("<II", data, o + 16, NEW_FSZ, NEW_FSZ)
            found = True
    assert found

    for base, words in ((STUBA_VA, STUBA), (CONV_VA, CONV)):
        for i, w in enumerate(words):
            struct.pack_into("<I", data, f(base) + i * 4, w)

    def hook(va, new, ok):
        o = e(va)
        cur = struct.unpack_from("<I", data, o)[0]
        assert cur in ok + (new,), "unexpected %08x at %#x" % (cur, va)
        struct.pack_into("<I", data, o, new)
    jal = lambda t: (3 << 26) | ((t >> 2) & 0x3FFFFFF)
    j_ = lambda t: (2 << 26) | ((t >> 2) & 0x3FFFFFF)
    hook(0x13AE5C, j_(STUBA_VA), (0x250B0017,))
    hook(0x221430, jal(CONV_VA), (0x0C068464,))
    hook(0x221444, jal(CONV_VA), (0x0C068464,))
    hook(0x22145C, 0x00000000, (0xA0600320,))
    hook(0x221460, 0x00000000, (0xA0600110,))
    return bytes(data)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "wb").write(apply(open(src, "rb").read()))
    print("backlog patch written:", dst)


if __name__ == "__main__":
    main()
