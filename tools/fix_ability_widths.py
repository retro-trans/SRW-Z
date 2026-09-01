# -*- coding: utf-8 -*-
"""Shorten the ability names that overflow their column in the Search grid.

Same grid, same budget, same cause as fix_skill_widths.py: four columns at
fixed x positions, fixed half-width font, ten characters per cell. 18 of the
40 names in this table were over it - "Photon Mat (Strong)" by nine.

THERE ARE TWO ABILITY TABLES IN COMPDATA and they disagree. The full list at
0x0694c0 says "Anti-Mind Attack", "Transform", "Repair Module", "HP Regen";
the SEARCH GRID at 0x070640 says "Anti-Psychic", "Transfm", "Repair Device",
"HP Recovery". Only the grid is touched here, and where a shorter form was
needed anyway it is aligned with the full list rather than invented again -
Repair Mod, Supply Mod, HP Regen, EN Regen, Anti-Mind.

"Transfm" is the odd one: it was ALREADY abbreviated, past readability, and
"Transform" fits the column at nine characters. Made longer, not shorter.

"Trinity Charge" becomes "Tri Charge", which is what the rest of the game
already calls it. " Reflector" had a stray leading space, the tell of an
earlier truncation.

Every replacement fits its existing field, so all are written in place and
NUL-padded - nothing moves and no pointer changes.

Usage: fix_ability_widths.py <iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
NAME = "COMPDATA.BN"
ROOM = 1823200 - 1823000

FIX = [
    (" Reflector",          "Reflector"),      # stray leading space
    ("Photon Mat (Strong)", "PhotonMat+"),
    ("Barrier Field",       "Bar Field"),
    ("Laminate Armor",      "Lam Armor"),
    ("Yata-no-Kagami",      "Yata"),
    ("Repair Device",       "Repair Mod"),     # full list says Repair Module
    ("Resupply Device",     "Supply Mod"),     # full list says Resupply Module
    ("Mach Special",        "Mach Spec"),
    ("HP Recovery",         "HP Regen"),       # full list says HP Regen (S-L)
    ("EN Recovery",         "EN Regen"),
    ("Transfm",             "Transform"),      # LONGER: it fits, and reads
    ("Tactical Swap",       "Tac Swap"),
    ("Mazin Power",         "Mazin Pwr"),
    ("Dizer Full Pwr",      "Dizer Full"),
    ("Subspace Dive",       "Subsp Dive"),
    ("Trinity Charge",      "Tri Charge"),     # what the rest of the game says
    ("Element System",      "Element"),
    ("Anti-Psychic",        "Anti-Mind"),      # full list says Anti-Mind Attack
    ("All Canceller",       "All Cancel"),
    ("Graviton Crit",       "Grav Crit"),
]


def table_entry(head):
    n = head.find(NAME.encode())
    while n >= 0:
        if head[n - 8:n] == (chr(92) * 2 + "DATA" + chr(92) * 2).encode():
            return n
        n = head.find(NAME.encode(), n + 1)
    raise SystemExit("file-table entry for COMPDATA.BN not found")


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "rb")
    head = f.read(4 * 1024 * 1024)
    n = table_entry(head)
    lba, sectors = struct.unpack_from("<II", head, n + 0x20)
    f.seek(lba * SECTOR)
    cur = f.read(max(sectors, ROOM) * SECTOR)
    f.close()
    d, _ = banlz.decompress_record(cur, 0)
    d = bytearray(d)

    done = skip = 0
    for old, new in FIX:
        ob, nb = old.encode("cp932"), new.encode("cp932")
        hits = []
        i = 0
        while True:
            i = bytes(d).find(ob, i)
            if i < 0:
                break
            z = bytes(d).find(b"\x00", i)
            if z - i == len(ob):
                hits.append(i)
            i += 1
        if not hits:
            print("NOT FOUND %r" % old)
            skip += 1
            continue
        ok = True
        for h in hits:
            z = bytes(d).find(b"\x00", h)
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            if len(nb) >= k - h:
                print("REFUSED %r -> %r needs %d, field holds %d"
                      % (old, new, len(nb) + 1, k - h))
                ok = False
                skip += 1
                break
        if not ok:
            continue
        for h in hits:
            z = bytes(d).find(b"\x00", h)
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            d[h:k] = nb + bytes(k - h - len(nb))
        done += len(hits)
        print("   %-20r -> %-12r %2d -> %2d ch, %d place(s)"
              % (old, new, len(old), len(new), len(hits)))
    print("%d field(s) changed, %d skipped" % (done, skip))
    if not write or not done:
        if not write:
            print("(dry run - pass --write to apply)")
        return 0

    blob = banlz.compress_record(bytes(d))
    back, _ = banlz.decompress_record(blob, 0)
    if back != bytes(d):
        raise SystemExit("banlz roundtrip failed - not writing")
    need = (len(blob) + SECTOR - 1) // SECTOR
    if need > ROOM:
        raise SystemExit("needs %d sectors, only %d free" % (need, ROOM))
    g = open(iso, "r+b")
    g.seek(lba * SECTOR)
    g.write(blob + bytes(sectors * SECTOR - len(blob)))
    g.seek(n + 0x24)
    g.write(struct.pack("<I", need))
    p = head.find(NAME.encode())
    rec = p - 33
    if struct.unpack_from("<I", head, rec + 2)[0] == lba:
        g.seek(rec + 10)
        g.write(struct.pack("<I", len(blob)))
        g.seek(rec + 14)
        g.write(struct.pack(">I", len(blob)))
    g.close()
    print("COMPDATA rewritten (%d bytes, %d sectors)" % (len(blob), need))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
