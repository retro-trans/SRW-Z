# -*- coding: utf-8 -*-
"""Repair three rows left corrupt after a longer name was written over a shorter one.

Found by tools/scan_broken_quotes.py 2026-08-26. Each row has a DUPLICATED TAIL:
the replacement text was written in place but the leftover bytes of the old,
longer string were never cleared, so the last few characters print twice.

    「...Moonlight Butterfly?!」ly?!」
    「...the Moon's Dianna!」nna!」
    「...with me.」 me.」

All three are also mis-attributed - the japanese speaker is ギンガナム, shipped as
"Dianna" - which is the same speaker bug tools/scan_speaker_mismatch.py reports
across 356 rows. rec106 additionally had Ghingnham calling himself head of
"House Dianna" where the japanese says ギンガナム家, and rec119's english is not a
truncation of the japanese at all but an unrelated line about the Moonlight
Butterfly, so both are retranslated from source.

Usage: fix_junk_tails.py <iso> [--write]
"""
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3
O, C = u"「", u"」"

# JP 「だが、小生はギンガナム家の総領。ディアナ・ソレルは貰い受ける」
# JP 「このギム・ギンガナムが月のディアナを売った反逆者に裁きを与える！」 (x2)
FIX = {
    (106, 0x0092b0): u"Ghingnham\n「But I am head of House\nGhingnham. Dianna Soreil comes\nwith me.」",
    (119, 0x017880): u"Ghingnham\n「I, Gym Ghingnham, shall pass\njudgment on the traitor who sold\nthe Moon's Dianna!」",
    (127, 0x01a3b0): u"Ghingnham\n「I, Gym Ghingnham, shall pass\njudgment on the traitor who sold\nthe Moon's Dianna!」",
}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def validate(new):
    body = new.split("\n")[1:]
    if len(body) > MAXLINES:
        return "%d body lines" % len(body)
    for b in body:
        if cols(b) > WIDTH:
            return "line %d cols: %r" % (cols(b), b)
    if new.count(O) != new.count(C):
        return "unbalanced kagi"
    try:
        new.encode("cp932")
    except UnicodeEncodeError as ex:
        return "not cp932: %r" % ex.object[ex.start:ex.end]
    return None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))

    edited, bad = {}, []
    for (n, off), new in sorted(FIX.items()):
        eb = bytearray(items[n][1])
        e = off
        while e < len(eb) and eb[e] != 0:
            e += 1
        k = e
        while k < len(eb) and eb[k] == 0:
            k += 1
        old = bytes(eb[off:e]).decode("cp932", "ignore")
        why = validate(new)
        if why:
            bad.append((n, off, why))
            continue
        nb = new.encode("cp932")
        if len(nb) >= k - off:
            bad.append((n, off, "needs %d bytes, slot %d" % (len(nb), k - off)))
            continue
        print("rec%-4d %#08x" % (n, off))
        print("   was %r" % old.replace("\n", " | "))
        print("   now %r" % new.replace("\n", " | "))
        eb[off:k] = nb + b"\x00" * (k - off - len(nb))
        edited[n] = bytes(eb)

    for b in bad:
        print("   REJECT rec%-4d %#08x %s" % b)
    if not write or not edited or bad:
        if bad:
            print("\nREFUSING to write while any row is rejected")
        elif not write:
            print("\n(dry run - pass --write to apply)")
        return

    for n, plain in edited.items():
        hdr = items[n][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        blob = banlz.compress_record(plain)
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(plain)
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % n
        print("   rec%-4d %d bytes (slot %d)" % (n, len(blob), nxt - hdr))
        sys.stdout.flush()
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for n, plain in edited.items():
        assert bytes(chk[n][1]) == plain, "readback mismatch rec %d" % n
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")


if __name__ == "__main__":
    main()
