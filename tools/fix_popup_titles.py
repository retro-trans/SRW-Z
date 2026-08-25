# -*- coding: utf-8 -*-
"""Translate the glossary-popup titles that dialogue links show.

The popup a 《term》 link opens is built from strings inside the scene's own
STAGE record - [title]["source"][description] - not from the keyword bank. The
descriptions were translated but several titles were left in Japanese or in
fullwidth Latin, so the link opened an English article under a Japanese
heading (「相克界」 over "A distortion layer above the world...").

Titles are replaced BY OFFSET, not by text, so the same word is untouched
where it appears in dialogue. Every replacement is shorter than the slot it
occupies, so nothing moves.

Left alone on purpose: "Side ３" and "２nd Battle of Jachin Due" keep their
fullwidth digits - this popup is drawn by the menu reader at 0x13A290, where
raw ASCII 0x2E-0x3D are control codes.

Usage: fix_popup_titles.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

FIX = [
    (2,  64880, u"\u5730\u7403\u9023\u5408", "Earth Alliance"),
    (25, 80904, u"Liff", "Ref"),                 # リフ; matches the bank entry
    (25, 81424, u"\u76f8\u514b\u754c", "Overlap"),
    (26, 58144, u"\u76f8\u514b\u754c", "Overlap"),
    (25, 82656, u"\uff35\uff2e", "UN"),
    (33, 12048, u"\uff35\uff2e", "UN"),
    (39, 15760, u"\uff35\uff2e", "UN"),
    (32, 44400, u"\uff26\uff21\uff29\uff34\uff28", "FAITH"),
    (39, 17560, u"\uff26\uff21\uff29\uff34\uff28", "FAITH"),
    (50, 61200, u"\uff26\uff21\uff29\uff34\uff28", "FAITH"),
    (88, 59320, u"\uff33\uff2f\uff26", "SOF"),
    (93, 10232, u"\uff33\uff2f\uff26", "SOF"),
]


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
    for idx, off, old, new in FIX:
        b = recs.setdefault(idx, bytearray(items[idx][1]))
        ob, nb = old.encode("cp932"), new.encode("cp932")
        assert bytes(b[off:off + len(ob)]) == ob, \
            "rec %d @%d holds %r, expected %r" % (idx, off, bytes(b[off:off + len(ob)]), ob)
        k = off + len(ob)
        while k < len(b) and b[k] == 0:
            k += 1
        assert len(nb) < k - off, "rec %d: %r does not fit %d bytes" % (idx, new, k - off)
        b[off:k] = nb + b"\x00" * (k - off - len(nb))
        print("rec %-4d @%-7d %-10s -> %-16s (slot %d)" % (idx, off, old, new, k - off))
    if dry:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(recs), jobs))
    pool = multiprocessing.Pool(jobs)
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
    print("done - %d titles in %d records" % (len(FIX), len(recs)))


if __name__ == "__main__":
    main()
