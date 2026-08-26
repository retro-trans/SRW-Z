# -*- coding: utf-8 -*-
"""Unescape literal backslash-quote in dialogue.

Reported from a screenshot 2026-08-26: Tekkouki's line renders

    Selling out that \\"researcher's soul\\" he named!?

scan_visible_defects.py checks for literal backslash-n and backslash-t but not
backslash-quote, so this survived every sweep. Same root cause as the literal
backslash-n bug: an escape that belonged to some intermediate JSON/py source
was written into the image verbatim.

Replacing with a plain ASCII double quote is safe: dialogue already contains 73
of them, so the font renders it. (The apostrophe is even more common - 42,383.)

Only 2 rows are affected, both in rec47, and both shrink by 2 bytes.

Usage: fix_escaped_quotes.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"
KAGI = u"「"
BS = chr(92)
PAIRS = [(BS + '"', '"'), (BS + "'", "'")]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, n = {}, 0
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        buf = bytearray(data)
        touched = False
        i, ln = 0, len(buf)
        while i < ln:
            j = buf.find(NUL, i)
            if j == -1:
                j = ln
            seg = bytes(buf[i:j])
            if len(seg) > 4:
                try:
                    s = seg.decode("cp932")
                except Exception:
                    i = j + 1
                    continue
                if KAGI in s:
                    new = s
                    for a, b in PAIRS:
                        new = new.replace(a, b)
                    if new != s:
                        enc = new.encode("cp932")
                        e = j
                        while e < ln and buf[e] == 0:
                            e += 1
                        if len(enc) <= e - i:
                            print("  rec%-4d off=%-7d" % (idx, i))
                            print("     %r" % s.replace("\n", " | "))
                            print("  -> %r" % new.replace("\n", " | "))
                            buf[i:e] = enc + NUL * (e - i - len(enc))
                            touched = True
                            n += 1
            i = j + 1
        if touched:
            edited[idx] = bytes(buf)

    print("\nrows fixed: %d in %d records" % (n, len(edited)))
    if not write or not edited:
        if not write:
            print("(dry run - pass --write to apply)")
        f.close()
        return

    import multiprocessing
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close()
    pool.join()
    for idx, plain in edited.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw))
             if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written")


if __name__ == "__main__":
    main()
