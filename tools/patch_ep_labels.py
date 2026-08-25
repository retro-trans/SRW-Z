# -*- coding: utf-8 -*-
"""Translate the 第/話 episode-marker kanji in the ELF label tables.

The 第15話 line on chapter title cards (and the intermission/save UI) is
COMPOSED at runtime: digits plus lone prefix/suffix label strings. The
digit-strip texture in RAM ("0123456789第話") is a glyph cache built from
those labels, so translating the labels is the whole fix - no texture work.

Sites (all inside label tables that are already English elsewhere -
"Funds/Name/Info/SR Point", " eps cleared", "Turns" - so plain ASCII is
proven safe here, unlike menu-encoded COMPDATA):
  0x445DA8  "第"        8B slot -> "Stage "   (title card / info prefix)
  0x445CD8  "話"        8B slot -> ""         (suffix; " eps cleared"
                                               already carries the words)
  0x4453F8  "話／"      8B slot -> "／"       (info row before "Turns")
  0x441F50  "第%s話『%s』に" 16B slot -> "Ep.%s: '%s'"  (stage-ref prompt)
  0x441F60  "第%s話『%s』を" 16B slot -> "Ep.%s: '%s'"

Usage: patch_ep_labels.py <iso> [--revert]   (idempotent, verifies old bytes)
"""
import sys

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80

LABELS = [
    # (va, slot, JP bytes, EN bytes)
    (0x445DA8, 8, bytes.fromhex("91e6"), b"Stage "),
    (0x445CD8, 8, bytes.fromhex("9862"), b""),
    (0x4453F8, 8, bytes.fromhex("9862815e"), bytes.fromhex("815e")),
    (0x441F50, 16, bytes.fromhex("91e62573986281772573817882c9"),
     b"Ep.%s: '%s'"),
    (0x441F60, 16, bytes.fromhex("91e62573986281772573817882f0"),
     b"Ep.%s: '%s'"),
]


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    with open(iso_path, "r+b") as iso:
        for va, slot, jp, en in LABELS:
            assert len(jp) < slot and len(en) < slot
            fo = ELF_LBA * SECTOR + (va - VBASE + FOFF)
            iso.seek(fo)
            cur = iso.read(slot)
            want_old, put = (en, jp) if revert else (jp, en)
            if cur == put + b"\x00" * (slot - len(put)):
                print("va %#x already patched" % va)
                continue
            assert cur.startswith(want_old) and cur[len(want_old)] == 0, \
                "va %#x holds unexpected bytes: %s" % (va, cur.hex())
            iso.seek(fo)
            iso.write(put + b"\x00" * (slot - len(put)))
            print("va %#x -> %r" % (va, put))
    print("done")


if __name__ == "__main__":
    main()
