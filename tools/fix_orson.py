# -*- coding: utf-8 -*-
u"""Reverse the Orson mis-rename: オルソン is "Olson", not "Orson".

name_source.json maps オルソン -> Olson (and オルソン・Ｄ・ヴェルヌ -> "Olson D.
Verne", ナイキック オルソン機 -> "Nikick (Olson)"). An earlier build "corrected"
Olson -> Orson across 519 STAGE rows and 14 COMPDATA fields and added a gate to
enforce it - the wrong direction. This puts it back.

"Orson" and "Olson" are both 5 bytes, so this is a pure same-length byte
replace: no offsets move, no pointers change, no box can overflow.

Also carries one dialogue reword that lives in an Orson record anyway (rec72),
so it is recompressed once instead of twice: Mizuki's 「戦いの事も」 was rendered
"In battle" (a fragment) instead of "about the war".

Usage: fix_orson.py <iso> [--write]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
STAGE_LBA, STAGE_SIZE = 1651029, 3910128
COMP_LBA, COMP_NSEC = 1823000, 74
OLD, NEW = b"Orson", b"Olson"
assert len(OLD) == len(NEW)

KO, KC = b"\x81\x75", b"\x81\x76"           # 「 」
# rec -> (old field bytes, new field bytes). Same-or-shorter, NUL-padded.
PRE_EDIT = {
    72: (b"Mizuki\n" + KO + b"Stubbornness gets tiring. In\nbattle, and about Touga and\nSandman." + KC,
         b"Mizuki\n" + KO + b"Putting on a front is tiring. The\nwar, and Touga and Sandman too." + KC),
}


def _compress(job):
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(data)
    return ri, blob


def rename_region(f, lba, size, is_stage, write):
    f.seek(lba * SEC)
    raw = bytearray(f.read(size))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    touched, total = {}, 0
    for ri, (hdr, d) in enumerate(live):
        changed = False
        if is_stage and ri in PRE_EDIT:
            a, b2 = PRE_EDIT[ri]
            k = d.find(a)
            if k >= 0:
                e = k + len(a)
                while e < len(d) and d[e] == 0:
                    e += 1
                slot = e - k
                assert len(b2) <= slot, "rec%d reword too long" % ri
                d[k:e] = b2 + b"\x00" * (slot - len(b2))
                changed = True
        n = d.count(OLD)
        if n:
            pos = 0
            while True:
                k = d.find(OLD, pos)
                if k < 0:
                    break
                d[k:k + len(OLD)] = NEW
                pos = k + len(NEW)
            total += n
            changed = True
        if changed:
            touched[ri] = d
    print("  %s: %d Orson in %d record(s)"
          % ("STAGE" if is_stage else "COMPDATA", total, len(touched)))
    if not touched or not write:
        return raw, total, False
    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, bytes(touched[ri])))
    got = {}
    # HALF the logical cores, not all-but-one. The optimal compressor is a
    # CPU- and memory-heavy pure-Python task; running one per logical core
    # oversubscribes the physical cores and each job runs 5-10x slower under
    # contention, which is what turned a ~2-minute batch into 15+ minutes.
    workers = max(1, (os.cpu_count() or 4) // 2)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for ri, blob in ex.map(_compress, [(r, n - h, dd) for r, h, n, dd in jobs]):
            got[ri] = blob
    for ri, hdr, nxt, dd in jobs:
        blob = got[ri]
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "record set changed"
    return raw, total, True


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    sraw, sn, sw = rename_region(f, STAGE_LBA, STAGE_SIZE, True, write)
    craw, cn, cw = rename_region(f, COMP_LBA, COMP_NSEC * SEC, False, write)
    if write:
        if sw:
            f.seek(STAGE_LBA * SEC)
            f.write(bytes(sraw))
        if cw:
            f.seek(COMP_LBA * SEC)
            f.write(bytes(craw))
        print("\nwritten: STAGE %s, COMPDATA %s" % (sw, cw))
    else:
        print("\n(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
