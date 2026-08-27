# -*- coding: utf-8 -*-
"""Rows whose SPEAKER LINE was emptied - the box renders completely blank.

Reported from a screenshot 2026-08-26: the ~Atlandia~ location card before
Johannes's first line showed an empty box, and its backlog entry was blank too.

    JP  '\u3000\n\u3000...～アトランディア～'   speaker line = fullwidth space
    EN  '\n            ~Atlandia~'          speaker line GONE, row opens with 0x0A

A row is `speaker\nbody`. When the japanese speaker line is a fullwidth space
(used for location cards and narration, so no name is drawn) and the translation
dropped it, the stored row begins with the newline and the box comes out empty.

scan_visible_defects.py checks for an empty BODY, never an empty speaker line,
so this class was invisible.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0


def main():
    iso = sys.argv[1]
    f = open(iso, "rb"); f.seek(LBA * SECTOR)
    en = banlz.decompress_all(f.read(SIZE)); f.close()
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())

    hits, byrec = [], collections.Counter()
    for idx in range(len(en)):
        e, j = en[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        e, j = bytes(e), bytes(j)
        seen = {}
        for p in range(0, min(len(e), len(j)) - 4, 4):
            ve = struct.unpack_from("<I", e, p)[0] - BASE
            vj = struct.unpack_from("<I", j, p)[0] - BASE
            if 0 <= ve < len(e) and 0 <= vj < len(j) and ve not in seen:
                seen[ve] = vj
        for eo, jo in seen.items():
            if e[eo:eo + 1] != b"\n":
                continue
            ze, zj = e.find(b"\x00", eo), j.find(b"\x00", jo)
            if ze <= eo or zj <= jo:
                continue
            try:
                se = e[eo:ze].decode("cp932")
                sj = j[jo:zj].decode("cp932")
            except Exception:
                continue
            if not sj.startswith("\n"):          # japanese HAD a speaker line
                hits.append((idx, eo, se, sj))
                byrec[idx] += 1

    print("rows that open with a bare newline (blank box): %d\n" % len(hits))
    print("worst records: %s" % byrec.most_common(8))
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 20
    for idx, eo, se, sj in hits[:lim]:
        print("rec%-4d %#08x" % (idx, eo))
        print("   EN %r" % se.replace("\n", " | ")[:70])
        print("   JP %r" % sj.replace("\n", " | ")[:60])


if __name__ == "__main__":
    main()
