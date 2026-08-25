# -*- coding: utf-8 -*-
"""Cut leftover garbage after a dialogue row's closing quote, and re-wrap rows
that sit one column over the box.

Found 2026-08-25 by tools/scan_visible_defects.py. Eight rows render trailing
junk after the proper closer:

    ...separate room...」」        extra 」
    ...Black History!」!」         extra !」
    ...transformation!?」?」       extra ?」
    ...broken robot army!」v       extra v

That is the signature of a shrink-without-padding write: some earlier pass wrote
a SHORTER string over a longer one and never NUL'd the tail, so the remnant of
the old string still renders up to the next NUL. (Every tool written on
2026-08-24/25 pads its slack - see fix_terms_global / fix_literal_nl_global.)

Only cut when the tail after the row's first closing 」 is SHORT (<= 3 chars).
A longer tail is not junk, it is a row with a second quoted span, and truncating
it would delete real dialogue.

Rows that are genuinely over 34 columns are re-wrapped instead, counting
placeholders EXPANDED.

Usage: fix_tail_junk.py <iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"
OPEN, CLOSE = u"「", u"」"
O, C = u"《", u"》"
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
MAX_JUNK = 3


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def wrap(body):
    out, cur = [], ""
    for t in body.split(" "):
        if not t:
            continue
        cand = t if not cur else cur + " " + t
        if ecols(cand) <= WIDTH:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = t
    if cur:
        out.append(cur)
    return out


def repair(s):
    """Return (new, what) or (None, reason)."""
    what = []
    op = s.find(OPEN)
    # Only ever cut a row with ONE quoted span. With two, the first CLOSE is an
    # inner closer and the text after it is real dialogue - truncating there
    # would delete it and leave the quotes unbalanced.
    if op != -1 and s.count(OPEN) == 1:
        cl = s.find(CLOSE, op)
        if cl != -1:
            tail = s[cl + 1:]
            if tail and len(tail) <= MAX_JUNK:
                s = s[:cl + 1]
                what.append("cut %r" % tail)
    lines = s.split("\n")
    body = lines[1:]
    if body and any(ecols(b) > WIDTH for b in body):
        joined = " ".join(l.strip() for l in body)
        joined = " ".join(joined.split())
        out = wrap(joined)
        if len(out) <= MAXLINES and all(l.count(O) == l.count(C) for l in out):
            s = "\n".join([lines[0]] + out)
            what.append("re-wrapped")
        else:
            what.append("STILL OVER - left alone")
    return (s, ", ".join(what)) if what else (None, "")


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
                if OPEN in s:
                    new, what = repair(s)
                    if new and new != s:
                        enc = new.encode("cp932")
                        e = j
                        while e < ln and buf[e] == 0:
                            e += 1
                        if len(enc) <= e - i:
                            print("  rec%-4d off=%-7d %s" % (idx, i, what))
                            print("      %r" % s.replace("\n", " | ")[:72])
                            print("   -> %r" % new.replace("\n", " | ")[:72])
                            buf[i:e] = enc + NUL * (e - i - len(enc))
                            touched = True
                            n += 1
            i = j + 1
        if touched:
            edited[idx] = bytes(buf)

    print("\nrows repaired: %d in %d records" % (n, len(edited)))
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


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


if __name__ == "__main__":
    main()
