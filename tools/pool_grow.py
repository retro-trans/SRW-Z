# -*- coding: utf-8 -*-
"""Grow one COMPDATA string past its slot, by moving it and repointing.

THE BUDGET IS NOT REAL, for this pool. pool.py established that COMPDATA's
single record is loaded at a hardcoded 0x006D6800 and used IN PLACE, and that
every string in the pool is reached through an ABSOLUTE RAM POINTER stored
earlier in the same record. Nothing indexes the pool by position. So a string
is only pinned to its offset by the pointers that name it - move both, and the
string can live anywhere.

There is somewhere to move it to: the record ends in **22,035 bytes of unused
padding**. That is the budget, and it is shared by every string that needs to
grow. Repacking the whole pool would reclaim a little more, but repack()
refuses without --allow-stray because 60 pointer-table entries deliberately aim
into a string's NUL padding or a few bytes INTO a string, and 0.8.81 broke all
60 by assuming they were coincidence. Relocating ONE string touches only the
pointers that name that string, so it does not go near them.

WHY THIS EXISTS. Episode 34 is 偽りの女王、仮面の姫 - "False Queen, Masked
Princess". Its field holds 23 characters and the full title needs 28, so the
noun had been dropped and the card read "False Queen, Masked", an adjective
with nothing to attach to. Every workaround inside 23 characters cost a word or
a register; moving the string cost neither.

REFUSES unless it is safe:
  * the string must be found exactly once in the pool
  * at least one pointer must name it, and EVERY pointer to it is rewritten
  * the destination must be inside the tail padding, 8-byte aligned, and
    entirely zero before the write
  * the new text must not collide with the next thing in the tail

Usage: pool_grow.py <iso> --old TEXT --new TEXT [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool

SECTOR = 2048
NAME = "COMPDATA.BN"
ROOM = 1823200 - 1823000


def table_entry(head):
    n = head.find(NAME.encode())
    while n >= 0:
        if head[n - 8:n] == (chr(92) * 2 + "DATA" + chr(92) * 2).encode():
            return n
        n = head.find(NAME.encode(), n + 1)
    raise SystemExit("file-table entry for COMPDATA.BN not found")


def tail_free(d):
    """First 8-byte-aligned offset of the unused run at the end of the pool."""
    end = len(d)
    while end > 0 and d[end - 1] == 0:
        end -= 1
    return (end + 8) & ~7


def main():
    iso = sys.argv[1]
    old = sys.argv[sys.argv.index("--old") + 1].encode("cp932")
    new = sys.argv[sys.argv.index("--new") + 1].encode("cp932")
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

    hits = []
    i = 0
    while True:
        i = d.find(old, i)
        if i < 0:
            break
        z = d.find(b"\x00", i)
        if z - i == len(old):          # a whole field, not a substring
            hits.append(i)
        i += 1
    if len(hits) != 1:
        raise SystemExit("found %d whole-field copies of %r - refusing"
                         % (len(hits), old.decode("cp932")))
    off = hits[0]
    ram = pool.BASE + off
    ptrs = [p for p in range(0, len(d) - 4, 4)
            if bytes(d[p:p + 4]) == struct.pack("<I", ram)]
    if not ptrs:
        raise SystemExit("no pointer names %#08x - refusing" % ram)

    dst = tail_free(d)
    if dst + len(new) + 1 > len(d):
        raise SystemExit("no room in the tail")
    if any(d[dst:dst + len(new) + 1]):
        raise SystemExit("destination %#08x is not empty" % dst)
    free = len(d) - dst

    print("%r" % old.decode("cp932"))
    print("   at pool %#08x (RAM %#08x), named by %d pointer(s): %s"
          % (off, ram, len(ptrs), ", ".join("%#08x" % p for p in ptrs)))
    z = d.find(b"\x00", off)
    k = z
    while k < len(d) and d[k] == 0:
        k += 1
    print("   old slot holds %d bytes; the new text needs %d"
          % (k - off, len(new) + 1))
    print("   moving to pool %#08x (RAM %#08x), %d bytes of tail free"
          % (dst, pool.BASE + dst, free))
    print("   -> %r" % new.decode("cp932"))
    if not write:
        print("(dry run - pass --write to apply)")
        return 0

    d[dst:dst + len(new)] = new
    d[dst + len(new)] = 0
    for p in ptrs:
        d[p:p + 4] = struct.pack("<I", pool.BASE + dst)
    # the old text is left where it was; nothing points at it any more, and
    # blanking it would only risk a pointer that aims INTO it (see pool.py's
    # 60 deliberate substring entries).

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
    print("moved and repointed (%d bytes, %d sectors)" % (len(blob), need))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
