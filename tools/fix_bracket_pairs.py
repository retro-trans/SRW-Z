# -*- coding: utf-8 -*-
"""Make the UI's hint brackets match each other.

35 COMPDATA strings open with a FULLWIDTH ＜ and close with an ASCII >:

    ＜All Units>        ＜Change the force name．>
    ＜Squad BGM>        ＜Support defend if a unit is able to．>

That is not carelessness, it is a workaround with a visible cost. ASCII '<' is
0x3C, inside the 0x2E-0x3D range the menu reader treats as CONTROL CODES, so
the opening bracket had to be widened to escape it. ASCII '>' is 0x3E, just
outside the range, so the closing one did not - and the pair ends up one glyph
wide and one narrow on screen.

Square brackets solve it properly: 0x5B and 0x5D are both outside the control
range, both half-width, and they SHRINK the string by one byte rather than
growing it, so nothing has to move. They also match the bracket style already
used for the cross-reference lines in the in-game help.

Only strings that open fullwidth and close ASCII are touched, and only when the
two are the outermost characters - a string using ＜ inside its text is left
alone.

Usage: fix_bracket_pairs.py <iso> [--write]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool

SECTOR = 2048
NAME = "COMPDATA.BN"
ROOM = 1823200 - 1823000
OP = u"\uff1c".encode("cp932")


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

    done = 0
    for m in list(re.finditer(re.escape(OP), bytes(d))):
        a = bytes(d).rfind(b"\x00", 0, m.start()) + 1
        z = bytes(d).find(b"\x00", m.start())
        if z < 0 or z - a > 120:
            continue
        raw = bytes(d[a:z])
        # the bracket does not have to open the string - "Info ＜Squad>" has
        # the same mismatch. What must hold is exactly ONE fullwidth ＜ and a
        # closing ASCII > at the end, so the pair is unambiguous.
        if raw.count(OP) != 1 or not raw.endswith(b">"):
            continue
        new = raw.replace(OP, b"[", 1)[:-1] + b"]"
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        if len(new) >= k - a:
            print("SKIP %#08x: would not fit" % a)
            continue
        d[a:k] = new + bytes(k - a - len(new))
        done += 1
        if done <= 6:
            print("   %#08x %r -> %r"
                  % (a, raw.decode("cp932", "replace")[:44],
                     new.decode("cp932", "replace")[:44]))
    print("%d bracket pair(s) made to match" % done)
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
