# -*- coding: utf-8 -*-
"""Measure translation coverage of the ENCYCLOPEDIA files (MTVZKN*).

status.py covers STAGE, COMPDATA and SRVC only, so the library was never in the
"100%" figures - the in-game Characters list still shows Japanese names.

  MTVZKNPT = pilot/character entries
  MTVZKNRT = robot/unit entries
  MTVZKNKW = keyword/glossary entries

All three are banlz containers and all three RELOCATE when they grow, so read
their current LBA from the game's own file table rather than a fixed offset.
"""
import os
import struct
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

SEC = 2048
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "iso",
                                                         "srwz_fix3.bin")
FILES = [("MTVZKNPT", b"\\\\DATA\\\\MTVZKNPT.BIN;1"),
         ("MTVZKNRT", b"\\\\DATA\\\\MTVZKNRT.BIN;1"),
         ("MTVZKNKW", b"\\\\DATA\\\\MTVZKNKW.BIN;1")]


def jp_chars(s):
    return sum(1 for c in s if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")


def real_text(s):
    if jp_chars(s) < 1:
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 and c != "\n":
            return False
        if 0xFF61 <= o <= 0xFF9F:
            return False
    good = sum(1 for c in s
               if jp_chars(c) or 0x20 <= ord(c) < 0x7F
               or 0xFF01 <= ord(c) <= 0xFF60 or c in u"　、。「」・ー…")
    return good / float(max(len(s), 1)) >= 0.6


f = open(ISO, "rb")
boot = f.read(0x120000)

for label, name in FILES:
    k = boot.find(name)
    if k < 0:
        print("%s: not in file table" % label)
        continue
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    f.seek(lba * SEC)
    blob = bytearray(f.read(nsec * SEC))
    try:
        recs = banlz.decompress_all(blob)
    except Exception as e:
        print("%s: decompress failed (%s)" % (label, e))
        continue
    en = jp = 0
    samples = []
    for idx, (off, data) in enumerate(recs):
        i = 0
        while i < len(data):
            j = data.find(b"\x00", i)
            if j < 0:
                break
            if j - i >= 2:
                try:
                    s = bytes(data[i:j]).decode("cp932")
                except UnicodeDecodeError:
                    s = None
                if s and real_text(s):
                    if jp_chars(s) >= 1:
                        jp += 1
                        if len(samples) < 8:
                            samples.append((idx, s))
                elif s and any(0x20 <= ord(c) < 0x7F for c in s) and len(s) > 2:
                    en += 1
            i = j + 1
    tot = en + jp
    print("%-9s LBA %-8d %3d recs | English %5d / %5d (%.1f%%) | Japanese %d"
          % (label, lba, len(recs), en, tot, 100.0 * en / max(tot, 1), jp))
    for idx, s in samples:
        print("      rec%-3d %s" % (idx, s[:44].replace("\n", " / ")))
f.close()
