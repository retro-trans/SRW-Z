# -*- coding: utf-8 -*-
u"""\u6708\u5149\u8776 in the weapon list: "Moonlight Btrfly" -> "Moonlight Butterfly".

A player reported "M-Fly Sys". Three different English forms ship for one
japanese weapon:

    STAGE dialogue   Moonlight Butterfly   26 rows, correct throughout
    weapon list      Moonlight Btrfly      6 pointer refs (COMPDATA)
    battle captions  M-Fly                 13 captions (SRVC)

The list form is a squeeze made against the OLD fixed-width assumption - 17
half-width characters. The column is 221 px and the font is proportional, so
"Moonlight Butterfly" measures **183 px and fits with 38 px to spare**; the
abbreviation buys nothing. tools/fit_weapon_names.py still carries the rule and
is corrected with it.

Edited IN PLACE inside the string's own slot: the entry has 7 spare bytes and
needs 3, so nothing is repacked and no pointer moves. That matters - the image
is ALREADY repacked, and apply_pool.py keys off the SHIPPED offsets, so running
it again here would either fail or move every string for a three-byte change.

The captions are a separate problem: a raw SRVC edit may not change a string's
length, and "Moonlight Butterfly" is 14 bytes longer than "M-Fly".

Usage: fix_moonlight_butterfly.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool
from patch import encode

SEC, LBA, NSEC = 2048, 1823000, 74
# (old, new) COMPDATA pool strings, edited in place inside their own slots.
PAIRS = [
    (u'Moonlight Btrfly', u'Moonlight Butterfly'),
    # Xabungle pilot names, akurasu ruling 2026-09-10 (see fix_plate_spellings)
    (u'Elche P', u'Elchi P'),
    (u'Elche P(E)', u'Elchi P(E)'),
    (u'Elche', u'Elchi'),
    (u'Daiku', u'Dike'),
]


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(NSEC * SEC))
    rec, used = banlz.decompress_record(raw, 0)
    rec = bytearray(rec)
    ents = list(pool.entries(bytes(rec)))
    hits = 0
    for OLD, NEW in PAIRS:
        ob, nb = encode(OLD, "menu"), encode(NEW, "menu")
        for s, t, sl in ents:
            if t != ob:
                continue
            print("%#08x  %-20r -> %-22r %d B into a %d B slot"
                  % (s, OLD, NEW, len(nb), sl - 1))
            if len(nb) > sl - 1:
                print("   REFUSED: does not fit its slot")
                f.close()
                return 1
            rec[s:s + sl] = nb + b"\x00" * (sl - len(nb))
            hits += 1
    if not hits:
        print("nothing left to fix in the pool")
        f.close()
        return 0
    blob = banlz.compress_record(bytes(rec))
    if len(blob) > NSEC * SEC:
        blob = banlz.compress_record_optimal(bytes(rec))
    if len(blob) > NSEC * SEC:
        print("REFUSED: recompressed %d B exceeds the %d B slot"
              % (len(blob), NSEC * SEC))
        f.close()
        return 1
    print("entries fixed: %d | COMPDATA recompresses to %d B (slot %d)"
          % (hits, len(blob), NSEC * SEC))
    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return 0
    chk, _ = banlz.decompress_record(bytearray(blob), 0)
    assert bytes(chk) == bytes(rec), "round-trip mismatch"
    f.seek(LBA * SEC)
    f.write(blob + b"\x00" * (NSEC * SEC - len(blob)))
    f.close()
    print("COMPDATA written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
