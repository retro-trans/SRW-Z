# -*- coding: utf-8 -*-
"""Translate the surnames left in kanji, which render glued to the given name.

18 pilot records carry flag 1 - "japanese name, concatenate field2+field3" -
with an untranslated SURNAME still in field2:

    \u795e + Hayato  -> "\u795eHayato"        \u7d05 + Eiji  -> "\u7d05Eiji"
    Computer Doll + No\uff0e \uff18 -> "Computer DollNo\uff0e \uff18"

The given names were translated and the surnames were not, so the two halves
ran together with no separator - flag 1 adds none, by design, because japanese
writes \u515c\u7532\u5150 with nothing between.

THE READINGS ARE NOT GUESSES. The game's own encyclopedia already carries the
full names, and it is unanimous: Hayato Jin, Kappei Jin, Gengoro Jin, Ichitaro
Jin, Umee Jin, Hanae Jin, Eiji Shigure, Reika Shigure. So \u795e reads Jin and \u7d05
reads Shigure - the latter a gikun, which is why it cannot be guessed from the
kanji. Hayato Jin is confirmed by the Getter Robo wiki as well.

The encyclopedia also says **Umee**, and the pilot record said "Ume". STAGE
agrees with the encyclopedia, 43 speaker lines to none, so the record was
wrong.

WHAT CHANGES. Each record is put into the project's western form - field2 =
given name with a TRAILING SPACE, field3 = surname - which is what flag 1
expects and what every other translated pilot already uses. Computer Doll is
not a person: it only ever needed the space, so field2 gains one and field3 is
left alone.

Schwarz + wald is in the same shape and is DELIBERATE - it composes
"Schwarzwald" - so it is not touched.

Usage: fix_glued_surnames.py <iso> [--write]
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
STRIDE = 176
ANCHOR = 0x009592

# (field2 now, field3 now) -> (field2 new, field3 new)
FIX = {
 (u"\u795e", u"Hayato"):   (u"Hayato ", u"Jin"),
 (u"\u795e", u"Kappei"):   (u"Kappei ", u"Jin"),
 (u"\u795e", u"Gengoro"):  (u"Gengoro ", u"Jin"),
 (u"\u795e", u"Ichitaro"): (u"Ichitaro ", u"Jin"),
 (u"\u795e", u"Ume"):      (u"Umee ", u"Jin"),
 (u"\u795e", u"Hanae"):    (u"Hanae ", u"Jin"),
 (u"\u7d05", u"Eiji"):     (u"Eiji ", u"Shigure"),
 (u"\u7d05", u"Reika"):    (u"Reika ", u"Shigure"),
 (u"Computer Doll", u"No\uff0e \uff18"): (u"Computer Doll ", u"No\uff0e \uff18"),
}
SLOT = 23                       # each name field is a 23-byte slot


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

    def s(o):
        z = d.find(b"\x00", o)
        return bytes(d[o:z]).decode("cp932", "replace") if z >= 0 else ""

    def ok(h):
        if h < 0 or h + STRIDE > len(d):
            return False
        return all(0 <= d.find(b"\x00", h + k) - (h + k) <= lim
                   for k, lim in ((0, 20), (21, 22), (44, 22)))

    lo = ANCHOR
    while ok(lo - STRIDE):
        lo -= STRIDE
    hi = ANCHOR
    while ok(hi + STRIDE):
        hi += STRIDE

    done = 0
    for h in range(lo, hi + 1, STRIDE):
        key = (s(h + 21), s(h + 44))
        if key not in FIX:
            continue
        f2, f3 = FIX[key]
        b2, b3 = f2.encode("cp932"), f3.encode("cp932")
        if len(b2) >= SLOT or len(b3) >= SLOT:
            raise SystemExit("%#08x: %r/%r will not fit a %d-byte field"
                             % (h, f2, f3, SLOT))
        d[h + 21:h + 21 + SLOT] = b2 + bytes(SLOT - len(b2))
        d[h + 44:h + 44 + SLOT] = b3 + bytes(SLOT - len(b3))
        done += 1
        print("   %#08x  %-16r -> %r" % (h, key[0] + key[1], f2 + f3))
    print("%d record(s) fixed" % done)
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
