# -*- coding: utf-8 -*-
u"""rec66: bracket the Meer lines the 0.9.38 rebracket pass had to skip, and
re-wrap the overflowing Durandal line.

The rebracket pass left ~200 rows unconverted because adding 「」 (2 columns,
2 bytes each side) would have pushed them over their box or slot. These four
are among them - three Meer lines (one still on ASCII quotes, two bare) and
Durandal's line, whose 2-line wrap ran 44 columns wide and spilled off the box.
Each is re-wrapped tighter so 「」 fits and every line is <= 30 columns.

Usage: fix_rec66_meer.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
KO, KC = b"\x81\x75", b"\x81\x76"
ELL = b"\x81\x63"                      # … fullwidth ellipsis

FIX = [
    # Meer, was ASCII "..." + hyphen; -> 「」, comma for the dash
    (0x1a060,
     b'Meer\n"...This war was surely born\nof the chaos from the birth of\na new world - the multiverse."',
     b"Meer\n" + KO + ELL + b"This war was surely born\nof the chaos from the birth of\na new world, the multiverse." + KC),
    # Meer, bare -> 「」, tightened
    (0x1a140,
     b"Meer\nWe should already know all\ntoo well the endless chain of\nhatred and the pain it brings!",
     b"Meer\n" + KO + b"We should know all too well\nthe endless chain of hatred\nand the pain it brings!" + KC),
    # Meer, bare -> 「」, tightened
    (0x1a1a0,
     b"Meer\nPlease wipe away the tears\nin your eyes and look ahead!",
     b"Meer\n" + KO + b"Please wipe the tears from\nyour eyes and look ahead!" + KC),
    # Durandal, 44-col overflow -> 3 lines <= 30, drop redundant "space"
    (0x1a4e0,
     b"Durandal\n" + KO + b"Did you know the Titans, who oppress space\ncolonists, also move under their command?" + KC,
     b"Durandal\n" + KO + b"Did you know the Titans, who\noppress colonists, also move\nunder their command?" + KC),
]


def slot_at(b, off):
    z = b.find(b"\x00", off)
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def cols(field):
    m = 0
    for line in field.split(b"\n"):
        c = i = 0
        while i < len(line):
            if line[i] in (0x81, 0x82, 0x83, 0x84, 0x85) or line[i] >= 0xE0:
                i += 2
            else:
                i += 1
            c += 1
        m = max(m, c)
    return m


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    hdr, d = live[66]
    for off, old, new in FIX:
        cur, slot = slot_at(d, off)
        if cur == new:
            continue
        assert cur == old, "@%#x mismatch\n have %r\n want %r" % (off, cur, old)
        assert len(new) <= slot, "@%#x new %d > slot %d" % (off, len(new), slot)
        c = cols(new)
        assert c <= 30, "@%#x still %d cols" % (off, c)
        d[off:off + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
        print("  @%#06x fixed (%d cols, %d/%d bytes)" % (off, c, len(new), slot))
    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return 0
    nxt = min([h for h in heads if h > hdr] or [len(raw)])
    room = nxt - hdr
    blob = banlz.compress_record(bytes(d))
    if len(blob) > room:
        blob = banlz.compress_record_optimal(bytes(d))
    assert len(blob) <= room, "rec66 over slot"
    raw[hdr:hdr + len(blob)] = blob
    for x in range(hdr + len(blob), nxt):
        raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.flush()
    os.fsync(f.fileno())
    f.close()
    print("rec66 written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
