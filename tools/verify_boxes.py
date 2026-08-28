# -*- coding: utf-8 -*-
"""Fail the build if a dialogue row is one column too wide for its box.

WHY THIS EXISTS. A hard emulator crash at the end of stage 1 survived four
clean gate runs. integrity, verify_pointers, verify_elf_patches and
verify_terms all passed a build carrying 1,137 latent crashes, because every
one of them checks STRUCTURE and this defect is about LAYOUT:

    v1.54   ???  "But get in our way, and we'll    1 + 29 = 30 columns
    v1.55  ???  「But get in our way, and we'll    2 + 29 = 31 columns

v1.55 converted ASCII " to 「」 and kept the old line breaks. " is one column,
「 is two, so any line sitting exactly ON the limit went one past it. A row
that already used all three body lines then spills to a fourth and overflows
the box. Nothing is malformed - valid bytes, balanced quotes, resolving
pointers, and the row is SHORTER than rows that work.

WHAT IT FLAGS. Only the regression signature: a row of three or more body
lines that is over the limit with 「」 but would be under it with ASCII
quotes. Rows that are wide on their own merit are NOT flagged - several were
tested at 34 columns and render fine, and flagging those would mean 12,954
false alarms.

Run it with the other gates, before every chdman.

Usage: verify_boxes.py <iso>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from fix_popup_wrap import sstrings, cols

SEC, LBA, SIZE = 2048, 1651029, 3910128
LIMIT = 30
KO, KC = u"\u300c", u"\u300d"


def main():
    f = open(sys.argv[1], "rb")
    f.seek(LBA * SEC)
    recs = banlz.decompress_all(f.read(SIZE))
    f.close()
    bad = []
    for ri, (_h, p) in enumerate(recs):
        if p is None:
            continue
        for off, s in sstrings(bytes(p)):
            if len(s) < 12 or b"\n" not in s or len(s) > 300:
                continue
            try:
                t = s.decode("cp932")
            except UnicodeDecodeError:
                continue
            if KO not in t:
                continue
            lines = t.partition("\n")[2].split("\n")
            if len(lines) < 3:
                continue
            w = max(cols(l) for l in lines)
            if w <= LIMIT:
                continue
            plain = max(cols(l.replace(KO, '"').replace(KC, '"')) for l in lines)
            if plain <= LIMIT:
                bad.append((ri, off, w, t.replace("\n", " | ")[:52]))
    if not bad:
        print("box gate OK: no row pushed over %d columns by its quote marks"
              % LIMIT)
        return 0
    print("OVERFLOW: %d row(s) are one column too wide for a 3-line box" % len(bad))
    for ri, off, w, t in bad[:12]:
        print("   rec %-4d 0x%06x  %d cols  %s" % (ri, off, w, t))
    if len(bad) > 12:
        print("   ... and %d more" % (len(bad) - 12))
    print("\nRun fix_quote_overflow.py - these crash the game when displayed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
