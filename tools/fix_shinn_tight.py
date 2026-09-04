# -*- coding: utf-8 -*-
u"""The 5 dialogue rows where Shin -> Shinn overflowed an exact-fit slot.

Each frees one byte by a small, meaning-preserving trim so "Shinn" fits.
(The 2 rec0 synopsis rows with the same problem are left - rec0 is the giant
record whose recompression is intractable, and the synopsis is rarely read.)

Usage: fix_shinn_tight.py <iso> [--write]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
KO, KC = b"\x81\x75", b"\x81\x76"
ELL = b"\x81\x63"                       # …

# (rec, offset, old, new)
FIX = [
    (67, 0x2e60,
     b"Athrun\n" + KO + b"Coming in, Shin." + KC,
     b"Athrun\n" + KO + b"Coming, Shinn." + KC),
    (67, 0x3330,
     b"Kamille\n" + KO + b"I think what Shin says is\nsound." + KC,
     b"Kamille\n" + KO + b"I think Shinn's right." + KC),
    (118, 0x1ed30,
     b"Banjo\n" + KO + b"So I really couldn't tell Shin\nabout her. That was around the\ntime of the Athrun thing." + KC,
     b"Banjo\n" + KO + b"So I couldn't tell Shinn\nabout her. That was around the\ntime of the Athrun thing." + KC),
    (118, 0x1f310,
     b"Four\n" + KO + b"I'm glad, Shin... Stella..." + KC,
     b"Four\n" + KO + b"I'm glad, Shinn... Stella" + ELL + KC),
    (135, 0x21029,
     b"Rey\n" + KO + b"Shut up, Shin! You betrayed the\nChairman, so you're my enemy! I've\nnothing to say to an enemy!" + KC,
     b"Rey\n" + KO + b"Shut up, Shinn! You betrayed the\nChairman, so you're my enemy!\nNothing to say to an enemy!" + KC),
]


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


def cols(field):
    m = 0
    for line in field.split(b"\n"):
        c = i = 0
        while i < len(line):
            i += 2 if (line[i] >= 0x81 and line[i] <= 0x9f) or line[i] >= 0xe0 else 1
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
    touched = {}
    for ri, off, old, new in FIX:
        d = live[ri][1]
        cur, slot = slot_at(d, off)
        if cur == new:
            continue
        assert cur == old, "rec%d @%#x mismatch\n have %r\n want %r" % (ri, off, cur, old)
        assert len(new) <= slot, "rec%d @%#x new %d > slot %d" % (ri, off, len(new), slot)
        assert cols(new) <= 34, "rec%d @%#x %d cols" % (ri, off, cols(new))
        d[off:off + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
        touched[ri] = d
        print("  rec%-3d @%#06x fixed (%d/%d bytes, %d cols)" % (ri, off, len(new), slot, cols(new)))
    if not touched or not write:
        if touched:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return 0
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
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written (%d records)" % len(touched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
