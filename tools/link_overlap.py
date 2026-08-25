# -*- coding: utf-8 -*-
"""Restore the 《Overlap》 links the Japanese script had, and one missed line.

The JP script marks 《相克界》 as a glossary link in 5 places - 4 in record 25,
1 in record 26 - and our English lost the markers, so the term was plain text
even though pressing Square still opened the entry.

SAFETY: a link whose scene does not carry the popup entry is a DEAD link, and
a dead link is what crashes the game. Only records 25 and 26 carry the Overlap
entry (verified against both the JP and the shipped data), and those are
exactly the two records the JP linked - so no link added here can be dead.

Record 106 said "Cross-Realm" - the same keyword, missed by unify_overlap.py
because that row was relocated so its offset no longer matches the JP. It is
renamed but deliberately NOT linked: record 106 has no entry of its own.

Usage: link_overlap.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from fix_placeholder_wrap import ecols, wrap
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

OPEN, CLOSE = u"\u300a", u"\u300b"
LINK = [(25, 88240), (25, 88368), (25, 96992), (25, 97344), (26, 60816)]
PLAIN = [(106, 56220)]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    recs = {}
    for idx, off in LINK + PLAIN:
        b = recs.setdefault(idx, bytearray(items[idx][1]))
        e = off
        while b[e] != 0:
            e += 1
        k = e
        while k < len(b) and b[k] == 0:
            k += 1
        parts = bytes(b[off:e]).decode("cp932").split("\n")
        flat = " ".join(parts[1:]).replace("Cross-Realm", "Overlap")
        if (idx, off) in LINK:
            flat = flat.replace("Overlap", OPEN + "Overlap" + CLOSE)
        lines = wrap(flat)
        assert len(lines) <= MAXLINES, "%d@%d: %d lines" % (idx, off, len(lines))
        for l in lines:
            assert ecols(l) <= WIDTH, "%d@%d: %d cols %r" % (idx, off, ecols(l), l)
        nb = u"\n".join([parts[0]] + lines).encode("cp932")
        assert len(nb) < k - off, "%d@%d: %d bytes > slot %d" % (idx, off, len(nb), k - off)
        b[off:k] = nb + b"\x00" * (k - off - len(nb))
        print("rec %-4d @%-7d %s" % (idx, off, "linked" if (idx, off) in LINK else "renamed"))
    if dry:
        return
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, [(i, bytes(b)) for i, b in recs.items()]))
    pool.close(); pool.join()
    for idx, b in recs.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(items[i][0] for i in recs), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed" % len(changed))


if __name__ == "__main__":
    main()
