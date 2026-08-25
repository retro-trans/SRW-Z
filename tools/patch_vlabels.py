# -*- coding: utf-8 -*-
"""Translate the VERTICAL labels on the in-battle unit/pilot status screens.

特殊スキル / 特殊能力 / 強化パーツ are ELF strings with a NEWLINE BETWEEN
EVERY CHARACTER (特\n殊\nス\nキ\nル) - the renderer stacks the lines to get
vertical text. That defeated every contiguous-SJIS search; they were found
by dumping the font cache (PCSX2 texture dump) and then regex-searching EE
RAM with per-char gaps. They live in a fixed-slot label table (16-byte
slots, va 0x443878/88/98) whose pointers are built at runtime, so the
strings must stay at their addresses: in-place, <= 15 bytes + NUL.

English, same vertical mechanism, FULLWIDTH letters (kanji-sized cells,
row counts match the Japanese so the section layout is untouched):
  特殊スキル (5 rows) -> ＳＫＩＬＬ   (5 rows)
  特殊能力   (4 rows) -> ＡＢＩＬ    (4 rows)
  強化パーツ (5 rows) -> ＰＡＲＴＳ  (5 rows)

Usage: patch_vlabels.py <iso> [--revert]   (idempotent, verifies old bytes)
"""
import sys

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80


def enc_vertical(text):
    return "\n".join(text).encode("cp932")


LABELS = [
    # (va, JP original bytes, EN replacement)
(0x443878, bytes.fromhex("93c10a8eea0a83580a834c0a838b"),
     enc_vertical(u"ＳＫＩＬＬ")),          # ＳＫＩＬＬ
    (0x443888, bytes.fromhex("93c10a8eea0a945c0a97cd"),
     enc_vertical(u"ＡＢＩＬ")),                # ＡＢＩＬ
    (0x443898, bytes.fromhex("8bad0a89bb0a83700a81620a8363"),
     enc_vertical(u"ＰＡＲＴＳ")),          # ＰＡＲＴＳ
]
SLOT = 16


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    with open(iso_path, "r+b") as iso:
        for va, jp, en in LABELS:
            assert len(en) < SLOT and len(jp) < SLOT
            fo = ELF_LBA * SECTOR + (va - VBASE + FOFF)
            iso.seek(fo)
            cur = iso.read(SLOT)
            want_old, put = (en, jp) if revert else (jp, en)
            if cur.startswith(put) and cur[len(put)] == 0:
                print("va %#x already patched" % va)
                continue
            assert cur.startswith(want_old) and cur[len(want_old)] == 0, \
                "va %#x holds unexpected bytes: %s" % (va, cur.hex())
            iso.seek(fo)
            iso.write(put + b"\x00" * (SLOT - len(put)))
            print("va %#x: %s" % (va, put.decode("cp932").replace("\n", "")))
    print("done")


if __name__ == "__main__":
    main()
