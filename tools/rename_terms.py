# -*- coding: utf-8 -*-
u"""Rename terms across every STAGE dialogue field, with slot checks.

A rename that is the same length or shorter is always safe: the field keeps its
place and no pointer moves. A rename that GROWS has to fit the field's slot
(the bytes up to the next field), so those are checked one by one and reported
when they do not fit rather than being truncated.

Replacements run in the order given, so list the longest form first when one
term is a prefix of another (Kotoseto before Kotoset).

Usage: rename_terms.py <iso> <renames.json> [--write]
       renames.json = [["old", "new"], ...]
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128


def fields(b):
    out = []
    i, n = 0, len(b)
    while i < n:
        if b[i] == 0:
            i += 1
            continue
        z = b.find(b"\x00", i)
        if z < 0:
            z = n
        t = b[i:z]
        if len(t) >= 2 and not any(c < 0x20 and c != 0x0A for c in t):
            e = z
            while e < n and b[e] == 0:
                e += 1
            out.append((i, t, e - i - 1))       # offset, text, slot
        i = z + 1
    return out


def main():
    iso = sys.argv[1]
    ren = [(a.encode("cp932"), b.encode("cp932"))
           for a, b in json.load(open(sys.argv[2], encoding="utf-8"))]
    write = "--write" in sys.argv

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytes(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    counts = collections.Counter()
    nofit = []
    touched = {}
    for ri, (hdr, be) in enumerate(live):
        d = bytearray(be)
        changed = False
        for off, t, slot in fields(be):
            nt = t
            for a, b in ren:
                if a in nt:
                    k = nt.count(a)
                    nt = nt.replace(a, b)
                    counts["%s -> %s" % (a.decode(), b.decode())] += k
            if nt == t:
                continue
            if len(nt) > slot:
                nofit.append((ri, off, len(nt), slot,
                              t.decode("cp932", "replace").replace("\n", " / ")[:60]))
                for a, b in ren:            # undo the count, it was not applied
                    if a in t:
                        counts["%s -> %s" % (a.decode(), b.decode())] -= t.count(a)
                continue
            d[off:off + slot + 1] = nt + b"\x00" * (slot + 1 - len(nt))
            changed = True
        if changed:
            touched[ri] = bytes(d)

    print("records touched: %d" % len(touched))
    for k, v in sorted(counts.items()):
        if v:
            print("   %-28s %d" % (k, v))
    print("fields that do not fit: %d" % len(nofit))
    for x in nofit:
        print("   rec%-4d @%#07x %d B > slot %d  %r" % x)
    if not touched or not write:
        if touched:
            print("\n(dry run - pass --write to apply)")
        return 0

    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(touched[ri])
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(touched[ri])
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written")
    return 0


raise SystemExit(main())
