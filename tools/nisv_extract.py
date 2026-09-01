# -*- coding: utf-8 -*-
"""Pull the in-game HELP/TUTORIAL text out of NISVDATA.BIN.

NISVDATA holds seven banlz records. Only two are prose:

    rec5    78 strings   the SR Point / difficulty explanation
    rec6  2042 strings   the whole help system - About Formation, About
                         Movement, About Attacking, spirit commands, squad
                         building, upgrading, the bazaar, the library...

rec0-rec2 are graphics; their "japanese" is binary decoding as kanji, and
translating it would corrupt the file. **rec3 is a KANJI READING DICTIONARY**
(なぐさ・める, うつく・しい) - the IME data for the japanese name-entry screen,
not prose. It is 5,240 strings and it is the reason this file looked like
7,734 untranslated lines when it is really about 2,250.

SHAPE. Every field is a self-contained title or one-line sentence, NUL
terminated, with room = length + 1. There is no slack, but japanese is two
bytes per character against roughly one for english, so a translation is
normally about half the size. The extractor records the room anyway, because
a field that would grow has to be caught before it is written, not after.

Usage: nisv_extract.py <iso> [--out FILE]
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "nisv_jp.json")
LBA, SECTORS = 1568269, 272
PROSE = (5, 6)
JP = re.compile(u"[\u3040-\u30ff\u4e00-\u9fa5\uff00-\uffef]")


def strings(b):
    i = 0
    while True:
        z = b.find(b"\x00", i)
        if z < 0:
            return
        if 2 < z - i < 400:
            try:
                t = b[i:z].decode("cp932")
            except UnicodeDecodeError:
                t = None
            if t and JP.search(t):
                k = z
                while k < len(b) and b[k] == 0:
                    k += 1
                yield i, t, z - i, k - i
                i = k
                continue
        i = z + 1


def main():
    iso = sys.argv[1]
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else OUT)
    f = open(iso, "rb")
    f.seek(LBA * 2048)
    recs = banlz.decompress_all(f.read(SECTORS * 2048))
    f.close()
    rows = []
    for ri in PROSE:
        b = bytes(recs[ri][1])
        for off, t, ln, room in strings(b):
            rows.append({"rec": ri, "off": off, "jp": t,
                         "bytes": ln, "room": room})
        print("rec%d: %d string(s)" % (ri, sum(1 for r in rows
                                               if r["rec"] == ri)))
    uniq = len(set(r["jp"] for r in rows))
    print("%d instance(s), %d unique, %d japanese characters"
          % (len(rows), uniq, sum(len(r["jp"]) for r in rows)))
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
