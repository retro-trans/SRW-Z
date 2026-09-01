# -*- coding: utf-8 -*-
"""Generate the hashed english for rec6's 17 section blurbs.

A blurb is the one- to three-line description shown beside each chapter of the
Strategy Q&A. They are addressed here BY OFFSET rather than by japanese text,
for the same reason the rest of this pipeline is hash-keyed: the source script
must not be committed. The generator reads the japanese from the disc, hashes
it, pairs it with the english below by position and writes hash/english only.

Line breaks are kept where the japanese has them - each field is one display
paragraph and the breaks are where the box wraps - so the english is written
as the same number of lines and each line is measured separately.

Run once against an image that still has the japanese here. After the
translation is applied the japanese is gone, and analysis/nisv_rec6_blurbs.json
is the record.

Usage: nisv_rec6_blurbs_gen.py <iso>
"""
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from nisv_extract import LBA, SECTORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "nisv_rec6_blurbs.json")
NL = chr(10)
FW = dict((chr(0x30 + i), chr(0xFF10 + i)) for i in range(10))
FW["."] = chr(0xFF0E)
FW[":"] = chr(0xFF1A)

# offset in rec6 -> english, in the order the chapters appear
EN = [
 (0x001301, "Ways to restore lost HP and EN."),
 (0x001324, "How spirit commands and SP work."),
 (0x00134b, "The kinds of ability a unit can have,\nand when each one helps."),
 (0x00138f, "The kinds of skill a pilot can learn,\nand when each one helps."),
 (0x0013db, "Upgrading and training units and pilots,\nand the numbers the bazaar runs on."),
 (0x00142f, "What squads do, and the leader and member roles."),
 (0x001464, "What to watch for when building a squad."),
 (0x001495, "A quicker way to build squads."),
 (0x0014b8, "What to watch for when swapping."),
 (0x0014db, "About pilot training, and what is\nworth putting points into."),
 (0x00151d, "Spending funds to upgrade units and weapons."),
 (0x001556, "About the parts you equip to a unit."),
 (0x001583, "Refitting a unit into another form."),
 (0x0015b4, "SR Points, the game's challenge to you."),
 (0x0015ef, "The bazaar, open in the intermission."),
 (0x001626, "Options, where game settings are changed,\n"
            "and the Library, where you can learn\nmore about the game."),
 (0x00168f, "Small things worth knowing."),
]


def fw(s):
    return "".join(FW.get(c, c) for c in s)


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(LBA * 2048)
    recs = banlz.decompress_all(f.read(SECTORS * 2048))
    f.close()
    b = bytes(recs[6][1])
    rows, bad = [], 0
    for off, en in EN:
        z = b.find(b"\x00", off)
        jp = b[off:z]
        k = z
        while k < len(b) and b[k] == 0:
            k += 1
        room = k - off
        text = fw(en)
        nb = text.encode("cp932")
        if len(nb) >= room:
            print("TOO LONG %#08x: needs %d, room %d" % (off, len(nb) + 1, room))
            print("   %r" % text)
            bad += 1
            continue
        if len(text.split(NL)) != len(jp.decode("cp932", "replace").split(NL)):
            print("LINE COUNT differs at %#08x (%d vs %d) - check the wrap"
                  % (off, len(text.split(NL)),
                     len(jp.decode("cp932", "replace").split(NL))))
        rows.append([hashlib.sha1(jp).hexdigest()[:16], text])
    print("%d blurb(s) hashed, %d refused" % (len(rows), bad))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    print("wrote %s" % OUT)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
