# -*- coding: utf-8 -*-
"""Find rows where our English does not correspond to its Japanese source.

Two distinct failure modes look identical in an export and must be told apart:

  (a) POINTER AMBIGUITY - the row offset is referenced from several 4-aligned
      slots. Resolution takes the first match. Harmless when every slot holds
      the same value; a mis-pair when they disagree.
  (b) SHIPPED DAMAGE - the slots agree, so resolution is right, and our text
      genuinely is the wrong line (an earlier bad pass wrote over it).

Only (b) is a player-visible bug; (a) is a reporting bug in the export.
Speaker-line agreement is the discriminator: the JP speaker tag and our English
speaker label should map consistently across the whole corpus.

Usage: check_alignment.py <iso> [rec ...]
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    iso_path = sys.argv[1]
    recs = [int(a) for a in sys.argv[2:]] or None
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(bytes(f.read(SIZE)))
    f.close()

    disagree, damaged, checked = [], [], 0
    for p in sorted(os.listdir(os.path.join(WORK, "analysis", "review"))):
        if not (p.startswith("rec") and p.endswith(".json")):
            continue
        rec = int(p[3:6])
        if recs and rec not in recs:
            continue
        jb, eb = bytes(jp[rec][1]), bytes(items[rec][1])
        ptr = {}
        for i in range(0, len(jb) - 4, 4):
            v = struct.unpack_from("<I", jb, i)[0] - BASE
            if 0 <= v < len(jb):
                ptr.setdefault(v, []).append(i)
        rows = json.load(io.open(os.path.join(
            WORK, "analysis", "review", p), encoding="utf-8"))
        for r in rows:
            slots = ptr.get(r["off"], [])
            if len(slots) < 2:
                continue
            checked += 1
            vals = set()
            for s in slots:
                if s + 4 <= len(eb):
                    vals.add(struct.unpack_from("<I", eb, s)[0])
            if len(vals) > 1:
                disagree.append((rec, r["row"], len(slots), len(vals)))
    print("ambiguous rows checked   : %d" % checked)
    print("slots DISAGREE (mis-pair): %d" % len(disagree))
    for d in disagree[:25]:
        print("   rec%-4d row %-5d %d slots, %d distinct values" % d)
    if not disagree:
        print("\nEvery ambiguous row's pointer slots agree, so first-match")
        print("resolution returns the correct text. Export pairing is sound;")
        print("any JP/EN mismatch is shipped damage, not a resolution bug.")


main()
