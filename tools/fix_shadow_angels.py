# -*- coding: utf-8 -*-
"""Give the Shadow Angels their names back in COMPDATA.

The twelve wing generals of Aquarion are written in kanji and READ as names:

    \u982d\u7fc5 Touma   \u97f3\u7fc5 Otoha   \u591c\u7fc5 Johannes   \u4e21\u7fc5 Moroha
    \u7df4\u7fc5 Renshi  \u525b\u7fc5 Goushi  \u53cc\u7fc5 Futaba     \u667a\u7fc5 Shiruha
    \u8a69\u7fc5 Sirius

The dialogue knows this - STAGE renders every one of them by name, and does so
UNANIMOUSLY: 229 speaker lines say Touma, 213 Sirius, 62 Moroha, 61 Otoha, 39
Johannes, 36 Futaba, 13 Shiruha, 12 Renshi, 5 Goushi, with not one exception
between them. COMPDATA translated the same kanji LITERALLY instead:

    Headwing  Soundwing  Nightwing  Bothwing  Trainwing
    Sturdywing  Twinwing  Wisewing  Poemwing

COMPDATA supplies the speaker label over a battle caption, so the same
character announced herself as "Moroha" in a cutscene and "Bothwing" in the
battle that followed. Reported from a screenshot: "who is Bothwing?"

\u8a69\u7fc5 -> Sirius looks like a collision, because \u30b7\u30ea\u30a6\u30b9 (Sirius de Alisia) is a
separate pilot with his own record. It is not our doing: \u591c\u7fc5 reads Johannes,
so these kanji are name-readings, and the game gives both characters the same
name. Kept as the dialogue has it rather than invented around.

Every replacement is shorter than the literal it replaces, so each is written
in place and NUL-padded; no field moves.

Usage: fix_shadow_angels.py <iso> [--write]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
NAME = "COMPDATA.BN"
ROOM = 1823200 - 1823000
FIX = [(b"Headwing", b"Touma"), (b"Soundwing", b"Otoha"),
       (b"Nightwing", b"Johannes"), (b"Bothwing", b"Moroha"),
       (b"Trainwing", b"Renshi"), (b"Sturdywing", b"Goushi"),
       (b"Twinwing", b"Futaba"), (b"Wisewing", b"Shiruha"),
       (b"Poemwing", b"Sirius")]


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

    total = 0
    for old, new in FIX:
        hits = [m.start() for m in re.finditer(re.escape(old), bytes(d))]
        whole = []
        for h in hits:
            z = d.find(b"\x00", h)
            # only a COMPLETE field, never a substring of a longer string
            if z - h == len(old):
                whole.append(h)
        print("   %-11s -> %-9s %d field(s)%s"
              % (old.decode(), new.decode(), len(whole),
                 "" if len(whole) == len(hits)
                 else "  (%d partial match(es) left alone)"
                      % (len(hits) - len(whole))))
        for h in whole:
            d[h:h + len(old)] = new + bytes(len(old) - len(new))
        total += len(whole)
    print("%d field(s) renamed" % total)
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
    sys.exit(main())
