# -*- coding: utf-8 -*-
u"""Ability DATA HELP: make every non-final line an EVEN number of bytes.

THE BUG. The panel counts its rows with a pass that steps TWO BYTES PER
CHARACTER - it assumes fullwidth text - and only notices a newline when it
lands exactly on one. Finding one costs a single byte, which flips the parity
for everything after it. Japanese descriptions are entirely fullwidth, so every
line is an even number of bytes and the scan never misses. Ours are mostly
1-byte ASCII, so newlines land on the wrong parity and the panel allocates too
few rows; the surplus lines are then drawn over each other or off the box.

The drawing pass is fine - it goes through patch_hwfont's MHOOK and honours
every newline - which is why the text that DOES appear is intact. Only the row
count is short.

    ability descriptions with newlines : 48
    losing lines in our build          : 35
    losing lines in the japanese       :  0

Verified against four panels before writing this:

    Tri Charge   no newline                  -> 1 row,  showed 1
    Mazin Power  newline at 27 (odd)         -> 1 row,  showed 1
    AAAAA/BBBBB/CCCCC diagnostic, 5 and 11   -> 1 row,  showed 1
    Unite        37 odd, 66 EVEN, 101 odd    -> 3 rows, showed 3

Unite is the one that proves the mechanism: it misses its first newline, finds
the second, and the single byte that costs re-aligns it so the third is found
too.

THE FIX is one byte: pad any odd-length non-final line with a trailing space,
which is invisible at end of line. The last line needs nothing - no newline
follows it. Where the slot has no room, a double space elsewhere in the string
is collapsed to pay for it; anything still short is reported, not fudged.

Usage: fix_help_line_parity.py <iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
COMP_LBA, COMP_NSEC = 1823000, 74
RAM = 0x006D6800
DESC_TABLE = 0x4c9d0          # parallel to the name table at 0x4c900


def rows_seen(s):
    """Simulate the panel's row count: +2 per char, +1 landing on a newline."""
    i, n = 0, 1
    while i < len(s):
        if s[i] == 0x0A:
            n += 1
            i += 1
        else:
            i += 2
    return n


def slot_at(b, off):
    z = b.find(b"\x00", off)
    if z < 0:
        return None, None
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def even_out(s, room):
    """Pad odd non-final lines to even. Returns (new, ok)."""
    lines = s.split(b"\n")
    need = sum(1 for l in lines[:-1] if len(l) % 2)
    if not need:
        return s, True
    if need > room:
        # try to pay for it by collapsing a double space
        for i, l in enumerate(lines):
            while need > room and b"  " in lines[i]:
                lines[i] = lines[i].replace(b"  ", b" ", 1)
                room += 1
        if need > room:
            return s, False
    out = [l + b" " if (j < len(lines) - 1 and len(l) % 2) else l
           for j, l in enumerate(lines)]
    return b"\n".join(out), True


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(COMP_LBA * SEC)
    raw = bytearray(f.read(COMP_NSEC * SEC))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    hdr, data = live[0][0], bytearray(live[0][1])

    seen, fixed, short = set(), 0, []
    for i in range(-40, 80):
        dp = DESC_TABLE + i * 4
        if dp < 0 or dp + 4 > len(data):
            continue
        dv = struct.unpack_from("<I", data, dp)[0] - RAM
        if not (0 <= dv < len(data)) or dv in seen:
            continue
        seen.add(dv)
        s, slot = slot_at(data, dv)
        if not s or b"\n" not in s:
            continue
        real = s.count(b"\n") + 1
        if rows_seen(s) >= real:
            continue                       # already lands right
        new, ok = even_out(s, slot - len(s))
        if not ok:
            short.append((dv, real, rows_seen(s), slot - len(s)))
            continue
        assert len(new) <= slot, "%#x: %d > %d" % (dv, len(new), slot)
        assert rows_seen(new) == real, "%#x still short after padding" % dv
        data[dv:dv + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
        fixed += 1

    print("descriptions corrected      : %d" % fixed)
    print("still short (need rewording): %d" % len(short))
    for dv, real, got, spare in short:
        print("   @%#08x  %d lines, panel counts %d, spare %d" % (dv, real, got, spare))

    if fixed:
        blob = banlz.compress_record(bytes(data))
        if len(blob) > COMP_NSEC * SEC:
            blob = banlz.compress_record_optimal(bytes(data))
        assert hdr + len(blob) <= COMP_NSEC * SEC, "COMPDATA overflows its slot"
        if write:
            raw[hdr:hdr + len(blob)] = blob
            f.seek(COMP_LBA * SEC)
            f.write(bytes(raw))
            print("\nCOMPDATA written (%d bytes compressed)" % len(blob))
    if not write:
        print("\n(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
