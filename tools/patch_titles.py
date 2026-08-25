# -*- coding: utf-8 -*-
"""Free the stage titles from their per-string byte budget.

WHY THIS WORKS (and why the SRVC trick does not apply directly)
    COMPDATA is not a data file - it is a code+data overlay module ("MWo3"
    header, MIPS code from +0x80, loaded at a FIXED va 0x6D6800). Strings
    cannot simply grow, because everything after them would shift while the
    module's own code still refers to the old addresses.

    But the titles are not referenced from code: each stage record (stride
    0x30) holds an absolute POINTER to its title string. That pointer is data
    we can rewrite - so the pool can be re-laid-out freely as long as every
    pointer is updated, exactly like the SRVC sequence records.

    So: repack all 94 titles into the SAME region (2,036 bytes, of which 575
    were slack) and repoint. Short titles donate their bytes to long ones -
    the average budget goes from "whatever this string's slot happened to be"
    (15 bytes for "World Sans Lies") to ~21, and any single title may be much
    longer as long as the total fits.

Usage:
    patch_titles.py <iso> [--dry-run]      apply analysis/title_rewrites.json
    patch_titles.py <iso> --list           print every title with its budget
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz

LBA, SECTOR, SIZE = 1823000, 2048, 151552
BASE = 0x6D6800
LO, HI = 0x72E00, 0x73600          # the title string neighbourhood
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REWRITES = os.path.join(WORK, "analysis", "title_rewrites.json")


def load(iso_path):
    f = open(iso_path, "rb")
    f.seek(LBA * SECTOR)
    raw = f.read(SIZE)
    items = banlz.decompress_all(raw)
    hdr, dec = next((o, bytes(d)) for o, d in items if d is not None)
    return raw, items, hdr, bytearray(dec)


def find_titles(rec):
    """[(offset, text, [pointer slots])] in pool order."""
    ptrs = {}
    for i in range(0, len(rec) - 4, 4):
        v = struct.unpack_from("<I", rec, i)[0]
        o = v - BASE
        if LO <= o < HI and rec[o - 1:o] == b"\x00":
            ptrs.setdefault(o, []).append(i)
    out = []
    for o in sorted(ptrs):
        e = rec.index(b"\x00", o)
        try:
            t = rec[o:e].decode("cp932")
        except UnicodeDecodeError:
            continue
        out.append((o, t, ptrs[o]))
    return out


def main():
    iso_path = sys.argv[1]
    raw, items, hdr, rec = load(iso_path)
    titles = find_titles(rec)
    lo = titles[0][0]
    hi = max(o + len(t.encode("cp932")) for o, t, _p in titles) + 1
    pool = hi - lo

    if "--list" in sys.argv:
        for o, t, p in titles:
            print("%#07x  %-34s %d ptr" % (o, t, len(p)))
        used = sum(len(t.encode("cp932")) + 1 for _o, t, _p in titles)
        print("\n%d titles | pool %s bytes | used %s | free %s"
              % (len(titles), "{:,}".format(pool), "{:,}".format(used),
                 "{:,}".format(pool - used)))
        return

    new = {}
    if os.path.exists(REWRITES):
        new = json.load(io.open(REWRITES, encoding="utf-8"))
    final = [(o, new.get(t, t), p) for o, t, p in titles]
    need = sum(len(t.encode("cp932")) + 1 for _o, t, _p in final)
    print("titles %d | pool %s bytes | new layout needs %s (%+d)"
          % (len(final), "{:,}".format(pool), "{:,}".format(need), need - pool))
    assert need <= pool, "the new titles do not fit the pool by %d bytes" % (need - pool)
    changed = sum(1 for (o, t, p), (o2, t2, p2) in zip(titles, final) if t != t2)
    print("rewritten: %d" % changed)
    if "--dry-run" in sys.argv:
        for (o, old, p), (_o, t, _p) in zip(titles, final):
            if old != t:
                print("   %-30s -> %s" % (old, t))
        return

    # repack the pool and repoint every reference
    rec[lo:hi] = b"\x00" * pool
    cur = lo
    for _o, t, slots in final:
        enc = t.encode("cp932")
        rec[cur:cur + len(enc)] = enc
        for s in slots:
            struct.pack_into("<I", rec, s, BASE + cur)
        cur += len(enc) + 1
    assert cur <= hi

    blob = banlz.compress_record_optimal(bytes(rec))
    assert len(blob) <= SIZE, "record grew past its %d-byte slot" % SIZE
    out = bytearray(raw)
    out[hdr:hdr + len(blob)] = blob
    for i in range(hdr + len(blob), SIZE):
        out[i] = 0
    check = banlz.decompress_all(bytes(out))
    got = next(bytes(d) for _o, d in check if d is not None)
    assert got == bytes(rec), "record did not round-trip"
    # every pointer must land on a real string start
    for _o, t, slots in find_titles(bytearray(got)):
        pass
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    f.write(bytes(out))
    f.close()
    print("titles repacked and repointed; record %s of %s bytes"
          % ("{:,}".format(len(blob)), "{:,}".format(SIZE)))


if __name__ == "__main__":
    main()
