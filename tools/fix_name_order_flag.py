# -*- coding: utf-8 -*-
"""Set the "name is already in display order" flag the swap pass forgot.

THE ACTUAL BUG, after two wrong fixes.

Each pilot record carries a byte at head+67 (base+69 to the code) that
compose_name at VA 0x35f12c tests:

    lb   v0, 69(v1)
    bne  v0, zero, ->C
    B    "%s\u30fb%s" % (field3, field2)     flag 0: japanese order, insert \u30fb
    C    "%s%s"   % (field2, field3)     flag 1: already in display order

So it is not a formatting bug at all. It is a boolean meaning "these two
fields are already in the order they should be drawn in, do not add a
separator", and the proof is in the data:

    Koji Kabuto   field2 'Koji '  flag 1  -> "Koji Kabuto"   correct on screen
    Jiron Amos    field2 'Jiron ' flag 0  -> "Amos\u30fbJiron"   the reported bug

Same layout, different flag. The 422-record swap that put 178 pilots into
western order rewrote field2/field3 and never touched the flag, so 322 records
were left claiming japanese order while holding western data.

All 933 flags in this image are still byte-identical to the japanese disc,
which is what confirms nothing has ever written them and that 0/1 are the only
values the game uses.

WHAT THIS DOES. For every record whose field2 ends with a TRAILING SPACE - our
marker for "given name, western order" - and whose field3 is set, the flag is
set to 1. Records that are not in western order are left alone, so they keep
the \u30fb and keep rendering correctly.

The protagonist is deliberately NOT affected. Their record is not in this
array: it is built at 0x195aac from the name-entry buffer in the save, in
japanese order, and its flag comes from the save too. It stays on branch B and
keeps drawing "Setsuko\u30fbOhara", which is what the user asked for.

Usage: fix_name_order_flag.py <iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
NAME = "COMPDATA.BN"
ROOM = 1823200 - 1823000
STRIDE = 176
FLAG = 67


def table_entry(head):
    n = head.find(NAME.encode())
    while n >= 0:
        if head[n - 8:n] == (chr(92) * 2 + "DATA" + chr(92) * 2).encode():
            return n
        n = head.find(NAME.encode(), n + 1)
    raise SystemExit("file-table entry for COMPDATA.BN not found")


def records(d):
    """Walk the 176-byte array out from a record we can name."""
    def ok(h):
        if h < 0 or h + STRIDE > len(d):
            return False
        z0 = d.find(b"\x00", h)
        z2 = d.find(b"\x00", h + 21)
        z3 = d.find(b"\x00", h + 44)
        return (0 <= z0 - h <= 20 and 0 <= z2 - (h + 21) <= 22
                and 0 <= z3 - (h + 44) <= 22)
    anchor = 0x009592                      # Jiron Amos
    if not ok(anchor):
        raise SystemExit("anchor record not where expected - array moved?")
    lo = anchor
    while ok(lo - STRIDE):
        lo -= STRIDE
    hi = anchor
    while ok(hi + STRIDE):
        hi += STRIDE
    return list(range(lo, hi + 1, STRIDE))


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
    heads = records(d)

    def s(o):
        z = d.find(b"\x00", o)
        return bytes(d[o:z]) if z >= 0 else b""

    todo = [h for h in heads
            if d[h + FLAG] == 0 and s(h + 21).endswith(b" ") and s(h + 44)]
    print("%d records in the array; %d are western with the flag still 0"
          % (len(heads), len(todo)))
    names = sorted(set((s(h + 21) + s(h + 44)).decode("cp932", "replace")
                       for h in todo))
    print("%d distinct pilots: %s%s"
          % (len(names), ", ".join(names[:10]),
             " ..." if len(names) > 10 else ""))
    if not write:
        print("(dry run - pass --write to apply)")
        return 0

    for h in todo:
        d[h + FLAG] = 1
    # nothing but single bytes changed, and none of them inside a string
    blob = banlz.compress_record(bytes(d))
    back, _ = banlz.decompress_record(blob, 0)
    if back != bytes(d):
        raise SystemExit("banlz roundtrip failed - not writing")
    need = (len(blob) + SECTOR - 1) // SECTOR
    if need > ROOM:
        raise SystemExit("recompressed COMPDATA needs %d sectors, only %d free"
                         % (need, ROOM))
    print("compressed %d bytes (%d sectors, %d free)" % (len(blob), need, ROOM))
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
    print("set the flag on %d records" % len(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
