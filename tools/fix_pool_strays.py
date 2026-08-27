# -*- coding: utf-8 -*-
"""Repair the pool pointers that 0.8.81's repack left behind.

THE BUG. tools/pool.py rewrote every pointer whose target landed EXACTLY on a
string start, and deliberately left 91 pointer-shaped words alone on the
reasoning that they were u16 pairs rather than pointers. That reasoning was
wrong for most of them: 60 of the 91 sit precisely on a pointer-table stride,
so they ARE table entries. They point either

  * into the NUL PADDING after a string  - a deliberate pointer to an EMPTY
    string, used for blank slots, or
  * a few bytes INTO a string - a deliberate substring.

Repacking removed the padding and moved every string, so those pointers now
land inside unrelated text. A blank slot that used to draw nothing now draws
garbage, repeated once per slot - which is what the spirit strip on the squad
and unit screens shows.

THE REPAIR. The repack preserved entry ORDER and count, so entry i in a
pre-repack image is entry i in the current one. For each stray word:

    old target -> owning entry i, delta d
    new value  = new_start[i] + d      if d is inside the text
               = new_start[i] + len    if d was in the padding (empty string,
                                        pointing at the string's own NUL)

Both cases preserve exactly what the pointer used to resolve to.

Usage: fix_pool_strays.py <iso> <pre-repack-iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool

SEC = 2048
LBA, NSEC = 1823000, 74


def load(iso):
    f = open(iso, "rb")
    f.seek(LBA * SEC)
    raw = f.read(NSEC * SEC)
    f.close()
    items = banlz.decompress_all(raw)
    if not items:
        raise SystemExit("no banlz record at LBA %d in %s" % (LBA, iso))
    return bytes(items[0][1])


def main():
    iso, ref = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    cur = load(iso)
    old = load(ref)

    e_old = pool.entries(old)
    e_cur = pool.entries(cur)
    print("entries: pre-repack %d, current %d" % (len(e_old), len(e_cur)))
    if len(e_old) != len(e_cur):
        raise SystemExit("entry count differs - the reference is not comparable")
    if e_old[-1][0] <= e_cur[-1][0]:
        raise SystemExit("%s does not look pre-repack (last string at %#x)"
                         % (ref, e_old[-1][0]))

    starts_old = set(a for a, _, _ in e_old)
    stray = pool.strays(old, starts_old)
    ptrs_old = pool.pointers(old, starts_old)
    ws = set(p for p, _ in ptrs_old)
    import collections
    gaps = collections.Counter(b - a for a, b in
                               zip([p for p, _ in ptrs_old], [p for p, _ in ptrs_old][1:]))
    strides = [g for g, n in gaps.most_common(8) if n > 20]

    # index the old entries so a target can be resolved to (entry, delta)
    olds = [(a, t, s) for a, t, s in e_old]
    curs = [(a, t, s) for a, t, s in e_cur]
    fixes, skipped = [], []
    for p, t in stray:
        table = any((p - s) in ws or (p + s) in ws for s in strides)
        # locate the owning entry: the last entry starting at or before t
        i = -1
        lo, hi = 0, len(olds) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if olds[mid][0] <= t:
                i = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if i < 0 or t >= olds[i][0] + olds[i][2]:
            skipped.append((p, t, "outside any entry slot"))
            continue
        if not table:
            skipped.append((p, t, "not on a pointer stride - left alone"))
            continue
        d = t - olds[i][0]
        oldlen = len(olds[i][1])
        newlen = len(curs[i][1])
        if d < oldlen:
            nd = min(d, newlen)          # substring; clamp if the text shrank
            kind = "substring +%d" % nd
        else:
            nd = newlen                  # padding -> the string's own NUL
            kind = "empty (was +%d pad)" % d
        fixes.append((p, t, curs[i][0] + nd, i, kind))

    print("strays examined      : %d" % len(stray))
    print("repaired             : %d" % len(fixes))
    print("left alone           : %d" % len(skipped))
    for p, t, why in skipped[:6]:
        print("   %#08x -> %#08x  %s" % (p, t, why))
    for p, t, nv, i, kind in fixes[:12]:
        txt = curs[i][1].decode("cp932", "ignore")[:24]
        print("   word %#08x: %#08x -> %#08x  entry %d %-22s %r"
              % (p, t, nv, i, kind, txt))
    if len(fixes) > 12:
        print("   ... %d more" % (len(fixes) - 12))

    buf = bytearray(cur)
    for p, t, nv, i, kind in fixes:
        struct.pack_into("<I", buf, p, pool.BASE + nv)
    # every repaired pointer must now resolve inside the pool
    for p, t, nv, i, kind in fixes:
        v = struct.unpack_from("<I", bytes(buf), p)[0] - pool.BASE
        assert pool.POOL_LO <= v < pool.POOL_HI, "repaired pointer out of pool"
    print("\nall repaired pointers resolve inside the pool")

    if not write or not fixes:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return
    blob = banlz.compress_record(bytes(buf))
    if len(blob) > NSEC * SEC:
        blob = banlz.compress_record_optimal(bytes(buf))
    if len(blob) > NSEC * SEC:
        raise SystemExit("REFUSED: recompressed %d > slot %d" % (len(blob), NSEC * SEC))
    out = bytearray(NSEC * SEC)
    out[:len(blob)] = blob
    f = open(iso, "r+b")
    f.seek(LBA * SEC)
    f.write(bytes(out))
    f.close()
    assert load(iso) == bytes(buf), "readback mismatch"
    print("written and verified (%d compressed bytes)" % len(blob))


if __name__ == "__main__":
    main()
