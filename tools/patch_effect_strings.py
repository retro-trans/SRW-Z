# -*- coding: utf-8 -*-
"""Translate the CODE-BUILT weapon-effect names on the weapon screen.

Like the movement types (patched in 0.8.31), these strings exist nowhere
on disc: the routine at 0x390B18/0x390B78 assembles them from lui/ori
immediates and stores them word by word into the display buffer.

  0x390B24..0x390B54  サイズ補正無視  4 stores at +300..+312 = 16 bytes
  0x390B78..0x390B94  バリア貫通      3 stores at +300..+308 = 12 bytes

Each immediate pair is rewritten so the same stores spell ASCII instead
(NUL-padded). Only letters and spaces are used - 0x2E-0x3D are control
bytes to this renderer.

Usage: patch_effect_strings.py <iso> [--revert]
"""
import struct
import sys

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80

# (name, [(lui_va, ori_va)...], english, original japanese)
SITES = [
    ("size-modifier",
     [(0x390B24, 0x390B2C), (0x390B38, 0x390B3C), (0x390B40, 0x390B48),
      (None, 0x390B50)],
     "Ignore Size", "サイズ補正無視"),
    ("barrier-pierce",
     [(0x390B78, 0x390B7C), (0x390B80, 0x390B88), (None, 0x390B90)],
     "Pierce", "バリア貫通"),
]


def words_of(text, n):
    b = text.encode("ascii") + b"\x00" * (n * 4 - len(text))
    assert len(b) == n * 4, (text, n)
    return [struct.unpack_from("<I", b, i * 4)[0] for i in range(n)]


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    iso = open(iso_path, "r+b")

    def rd(va):
        iso.seek(ELF_LBA * SECTOR + (va - VBASE + FOFF))
        return struct.unpack("<I", iso.read(4))[0]

    def wr(va, word):
        iso.seek(ELF_LBA * SECTOR + (va - VBASE + FOFF))
        iso.write(struct.pack("<I", word))

    for name, pairs, en, jp in SITES:
        text = jp if revert else en
        raw = text.encode("cp932") if revert else text.encode("ascii")
        vals = words_of(text if not revert else "", len(pairs)) if not revert else None
        if revert:
            b = raw + b"\x00" * (len(pairs) * 4 - len(raw))
            vals = [struct.unpack_from("<I", b, i * 4)[0] for i in range(len(pairs))]
        for (lui_va, ori_va), val in zip(pairs, vals):
            hi, lo = (val >> 16) & 0xFFFF, val & 0xFFFF
            if lui_va is not None:
                w = rd(lui_va)
                assert (w >> 26) == 0x0F, "%#x is not lui" % lui_va
                wr(lui_va, (w & 0xFFFF0000) | hi)
            w = rd(ori_va)
            assert (w >> 26) == 0x0D, "%#x is not ori" % ori_va
            if lui_va is None:
                assert hi == 0, "%r needs a lui slot for %#06x" % (text, hi)
            wr(ori_va, (w & 0xFFFF0000) | lo)
        print("%-15s -> %r" % (name, text))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
