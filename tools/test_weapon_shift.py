# -*- coding: utf-8 -*-
"""EXPERIMENT: grow one weapon name and shift the rest of the list.

Question this answers: does the game find a weapon name by WALKING the packed
list to the Nth entry, or by a stored offset?

  walk    -> shifting entries is harmless, the whole list can be repacked, and
             the ~8.4KB of slack becomes available for full-length names
  offset  -> shifting silently breaks every name after the change

There is no pointer table (tested: 2 coincidental matches against 607 name
offsets over five bases), the list is packed on an 8-byte grid, and COMPDATA is
decompressed to RAM so the ELF reference cannot be found statically. So the
question is settled by running the game, not by reading it.

The experiment changes exactly ONE name:

    0x66f48  'MusouSw' (slot 8)  ->  'Musou Sword' (needs 12 -> slot 16)

Everything after 0x66f48 shifts 8 bytes later. The region ends with 112 free
bytes so it fits without touching the unit-name list at 0x6C000.

WHAT TO CHECK IN GAME - God Sigma's weapon list:

    Spin Saucer / God Tomahawk / Finger Needle / God Strings
    MusouSw  <- should now read "Musou Sword"
    Hissatsu Musou

  then check a LATER unit's weapons (anything after God Sigma in the list).

  correct everywhere            -> walk. Repack and expand all 11 short names.
  God Sigma right, others wrong -> stored offsets. Revert.
  garbage / shifted by one      -> stored offsets. Revert.

Usage: test_weapon_shift.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, NSEC = 1823000, 74
WPN_LO, WPN_HI = 0x66380, 0x6C000
NUL = b"\x00"

TARGET_OFF = 0x66F48
OLD = b"MusouSw"
NEW = b"Musou Sword"

# RESULT, 2026-08-26: the game uses STORED OFFSETS. Growing entry N by 8 bytes
# left entry N+1's offset pointing 8 bytes into the NEW string, and the weapon
# list rendered:
#
#     Musou Sword      <- grown entry, correct
#     ord              <- entry N+1, read from 0x66f50, the tail of "Musou Sword"
#
# "ord" is literally bytes 8..10 of "Musou Sword". Conclusive: the list is NOT
# walked, and repacking it would corrupt every name after the first change.
#
# RESOLVED the same day: the "offset table" is a table of ABSOLUTE PS2 RAM
# ADDRESSES stored inside COMPDATA itself (the record loads at a hardcoded
# 0x006D6800, so a name reference reads 0x0073D628). Every static search here
# failed because it looked for an index or a relative offset. See tools/pool.py,
# which repacks the pool and rewrites all 9,483 pointers - the budget is gone.
#
# This script is kept only as the record of how the question was settled. Do not
# run it: repacking through tools/apply_pool.py is the supported path.


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(NSEC * SEC))
    rec = bytearray(banlz.decompress_all(bytes(raw))[0][1])

    cur = bytes(rec[TARGET_OFF:TARGET_OFF + len(OLD)])
    if cur != OLD:
        print("REFUSED: expected %r at %#x, found %r" % (OLD, TARGET_OFF, cur))
        f.close()
        sys.exit(1)

    # old entry occupies its 8-byte slot; the new one needs 16
    old_slot = 8
    new_slot = ((len(NEW) + 1 + 7) // 8) * 8
    delta = new_slot - old_slot
    print("entry at %#x: %r (slot %d) -> %r (slot %d), shift %+d"
          % (TARGET_OFF, OLD.decode(), old_slot, NEW.decode(), new_slot, delta))

    # The region has NO free padding at the end, so the 8 bytes are borrowed
    # from the nearest FOLLOWING entry whose slot has at least that much slack.
    # Only the entries BETWEEN the two move, which keeps the blast radius tiny -
    # and here they are God Sigma's own weapons, so a stored-offset failure
    # shows up on the very screen being checked.
    p = TARGET_OFF + old_slot
    donor = None
    while p < WPN_HI:
        e = rec.find(NUL, p)
        if e < 0 or e >= WPN_HI:
            break
        k = e
        while k < WPN_HI and rec[k] == 0:
            k += 1
        used = e - p + 1
        slot = k - p
        shrunk = ((used + 7) // 8) * 8
        if slot - shrunk >= delta and e > p:
            donor = (p, bytes(rec[p:e]), slot, shrunk)
            break
        p = k
    if not donor:
        print("REFUSED: no following entry has %d bytes of slack" % delta)
        f.close()
        sys.exit(1)
    dp, dname, dslot, dshrunk = donor
    print("borrowing %d bytes from %#x %r (slot %d -> %d)"
          % (delta, dp, dname.decode("cp932", "ignore"), dslot, dshrunk))
    moved = (dp - (TARGET_OFF + old_slot))
    print("entries between the two shift +%d bytes (%d bytes of content)"
          % (delta, moved))

    newrec = bytearray(rec)
    middle = bytes(rec[TARGET_OFF + old_slot:dp])
    q = TARGET_OFF
    newrec[q:q + new_slot] = NEW + NUL * (new_slot - len(NEW))
    q += new_slot
    newrec[q:q + len(middle)] = middle
    q += len(middle)
    newrec[q:q + dshrunk] = dname + NUL * (dshrunk - len(dname))
    q += dshrunk
    assert q == dp + dslot, "repack arithmetic off: %#x vs %#x" % (q, dp + dslot)
    assert len(newrec) == len(rec), "record length changed"

    # show the neighbourhood so the shift is visible before writing
    print("\nafter the change:")
    p = TARGET_OFF
    for _ in range(6):
        e = newrec.find(NUL, p)
        k = e
        while k < len(newrec) and newrec[k] == 0:
            k += 1
        print("   %#08x slot=%-3d %r"
              % (p, k - p, bytes(newrec[p:e]).decode("cp932", "ignore")))
        p = k

    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return

    blob = banlz.compress_record_optimal(bytes(newrec))
    if len(blob) > NSEC * SEC:
        print("REFUSED: recompressed %d > slot %d" % (len(blob), NSEC * SEC))
        f.close()
        sys.exit(1)
    out = bytearray(NSEC * SEC)
    out[:len(blob)] = blob
    f.seek(LBA * SEC)
    f.write(bytes(out))
    f.close()
    g = open(iso, "rb")
    g.seek(LBA * SEC)
    chk = banlz.decompress_all(bytes(bytearray(g.read(NSEC * SEC))))
    g.close()
    assert bytes(chk[0][1]) == bytes(newrec), "readback mismatch"
    print("\nwritten and verified")


if __name__ == "__main__":
    main()
