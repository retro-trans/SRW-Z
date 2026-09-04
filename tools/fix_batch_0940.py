# -*- coding: utf-8 -*-
u"""Screenshot batch: weapon name, one stray name, one grammar fix.

  Gravity Lang -> Gravity Rang. ラング on a boomerang-type Overman weapon is
    "Rang" (cf. King Gainer's "Gainer Rang"), not "Lang". name_source had the
    transliteration wrong; COMPDATA carries the shipped string.
  Ruburu -> Lubul. ルブル is Lubul Wong Dalla; the speaker plate already says
    Lubul, one in-line vocative said "Ruburu".
  Scirocco: "a foe not to underestimate" -> "not a foe to underestimate"
    (侮れん相手 - the original was ungrammatical).

Same-region STAGE edits are in place inside their slots; COMPDATA is a
same-length byte replace (Gravity Lang and Gravity Rang are both 12 bytes).

Usage: fix_batch_0940.py <iso> [--write]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
STAGE_LBA, STAGE_SIZE = 1651029, 3910128
COMP_LBA, COMP_NSEC = 1823000, 74
KO, KC = b"\x81\x75", b"\x81\x76"

# STAGE (rec, offset, old field, new field)
STAGE_FIX = [
    (60, 0xde80,
     b"Miiya\n" + KO + b"Did you see, Ruburu? That girl\nselling oranges at the market\nseemed to be Dianna Soreil." + KC,
     b"Miiya\n" + KO + b"Did you see, Lubul? The girl\nselling oranges at the market\nlooked like Dianna Soreil." + KC),  # re-wrapped: Lubul is shorter, keep line 1 <=30 cols
    (58, 0xb790,
     b"Scirocco\n" + KO + b"$c, a foe not to\nunderestimate." + KC,
     b"Scirocco\n" + KO + b"$c... not a foe to\nunderestimate." + KC),
]
COMP_FIX = (b"Gravity Lang", b"Gravity Rang")   # same length


def _compress(job):
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(data)
    return ri, blob


def slot_at(b, off):
    z = b.find(b"\x00", off)
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")

    # ---- STAGE ----
    f.seek(STAGE_LBA * SEC)
    raw = bytearray(f.read(STAGE_SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    touched = {}
    for ri, off, old, new in STAGE_FIX:
        d = live[ri][1]
        cur, slot = slot_at(d, off)
        if cur == new:
            continue
        assert cur == old, "rec%d @%#x mismatch\n have %r\n want %r" % (ri, off, cur, old)
        assert len(new) <= slot, "rec%d new too long (%d>%d)" % (ri, len(new), slot)
        d[off:off + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
        touched[ri] = d
        print("  rec%-3d @%#06x fixed" % (ri, off))
    if touched and write:
        jobs = []
        for ri in sorted(touched):
            hdr = live[ri][0]
            nxt = min([h for h in heads if h > hdr] or [len(raw)])
            jobs.append((ri, hdr, nxt, bytes(touched[ri])))
        got = {}
        with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2)) as ex:
            for ri, blob in ex.map(_compress, [(r, n - h, dd) for r, h, n, dd in jobs]):
                got[ri] = blob
        for ri, hdr, nxt, dd in jobs:
            blob = got[ri]
            assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
            raw[hdr:hdr + len(blob)] = blob
            for x in range(hdr + len(blob), nxt):
                raw[x] = 0
        f.seek(STAGE_LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written (%d records)" % len(touched))

    # ---- COMPDATA (same-length) ----
    f.seek(COMP_LBA * SEC)
    craw = bytearray(f.read(COMP_NSEC * SEC))
    clive = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(craw))
             if isinstance(h, int) and d is not None]
    hdr, cd = clive[0]
    n = cd.count(COMP_FIX[0])
    print("  COMPDATA: %d x %s -> %s" % (n, COMP_FIX[0].decode(), COMP_FIX[1].decode()))
    if n and write:
        cd[:] = bytes(cd).replace(*COMP_FIX)
        blob = banlz.compress_record(bytes(cd))
        if len(blob) > COMP_NSEC * SEC:
            blob = banlz.compress_record_optimal(bytes(cd))
        assert hdr + len(blob) <= COMP_NSEC * SEC
        craw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), COMP_NSEC * SEC):
            craw[x] = 0
        f.seek(COMP_LBA * SEC)
        f.write(bytes(craw))
        print("COMPDATA written")

    if not write:
        print("\n(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
