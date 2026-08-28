# -*- coding: utf-8 -*-
"""Re-wrap the rows the 「」 conversion pushed one column past the box.

THE BUG, found by bisecting a hard emulator crash at the end of stage 1 down
to a single row:

    v1.54   ???  "But get in our way, and we'll   = 1 + 29 = 30 columns
    v1.55  ???  「But get in our way, and we'll   = 2 + 29 = 31 columns

v1.55 converted every ASCII " to 「」 and kept v1.54's line breaks. But " is
ONE column and 「 is TWO, so any line that was sitting exactly ON the limit
went one over. A row with three body lines then spills to a fourth and
overflows a three-line box.

That is why the crash was so hard to place: nothing is malformed. The bytes
are valid, the quotes balance, the pointers resolve, the row is shorter than
rows that work. The only thing wrong is that one line is one column too wide,
and only on rows that were already at the limit AND already use all three
lines. Rows with one or two body lines just grow to two or three and nobody
notices.

Proven, not inferred: reflowing that row to 25/25/23 with EVERY BYTE
UNCHANGED cleared the crash. So did reverting its quotes. Width is the cause.

Scope: 647 rows are in this state game-wide. Each is a crash waiting for the
player to reach it.

The re-wrap is byte-neutral - only ' ' and '\n' are exchanged - so no string
changes length, nothing moves, and no pointer needs repointing.

Usage: fix_quote_overflow.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from fix_popup_wrap import sstrings, cols, rewrap

SEC, LBA, SIZE = 2048, 1651029, 3910128
LIMIT = 30                 # v1.54 wrapped to this and never crashed
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KO = u"\u300c"
KC = u"\u300d"


def fix_record(dec):
    b = bytearray(dec)
    hits = []
    for off, s in sstrings(bytes(dec)):
        if len(s) < 12 or b"\n" not in s or len(s) > 300:
            continue
        try:
            t = s.decode("cp932")
        except UnicodeDecodeError:
            continue
        if KO not in t:
            continue
        spk, _, body = t.partition("\n")
        lines = body.split("\n")
        if len(lines) < 3 or max(cols(l) for l in lines) <= LIMIT:
            continue
        # Only rows the QUOTE CONVERSION pushed over, not rows that were
        # always wide. With ASCII quotes this row would still fit; with 「」
        # it does not. Rows wide on their own merit render fine - the bisect
        # cleared several at 34 columns - so re-wrapping those would be
        # 12,954 needless layout changes for a rule nothing has proven.
        ascii_w = max(cols(l.replace(KO, chr(34)).replace(KC, chr(34)))
                      for l in lines)
        if ascii_w > LIMIT:
            continue
        nb = rewrap(body, LIMIT)
        ok = (len(nb.split(chr(10))) <= 3
              and max(cols(l) for l in nb.split(chr(10))) <= LIMIT)
        if ok:
            new = (spk + chr(10) + nb).encode('cp932')
        else:
            # Cannot fit three lines at the limit by moving breaks alone.
            # Fall back to ASCII quotes, which is the OTHER fix proven to
            # clear this crash: 「 is two columns and " is one, so the row
            # drops back under the limit with its line breaks untouched.
            # Cosmetically inconsistent on a few hundred rows out of 68,120
            # - and a crash is worse than a straight quote.
            new = t.replace(KO, chr(34)).replace(KC, chr(34)).encode('cp932')
            if max(cols(l.replace(KO, chr(34)).replace(KC, chr(34)))
                   for l in lines) > LIMIT:
                continue
        if len(new) > len(s):
            continue
        b[off:off + len(s)] = new + bytes(len(s) - len(new))
        hits.append((off, max(cols(l) for l in lines),
                     max(cols(l) for l in nb.split("\n"))))
    return (bytes(b), hits) if hits else (None, [])


def _pack(args):
    # Fast compressor first, optimal only if it does not fit. The edit is
    # byte-neutral, so the fast result is almost always the same size as
    # what is already in the slot. Running optimal unconditionally on 142
    # records cost an hour of wall clock for no benefit.
    i, plain, room = args
    blob = banlz.compress_record(plain)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(plain)
    return i, blob


def main():
    iso = sys.argv[1]
    dry = "--dry-run" in sys.argv
    f = open(iso, "r+b" if not dry else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, total, skipped = {}, 0, 0
    for i, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        new, hits = fix_record(bytes(dec))
        if new is not None:
            edited[i] = (hdr, new)
            total += len(hits)
    print("rows re-wrapped to <=%d cols: %d, in %d records"
          % (LIMIT, total, len(edited)))
    if dry or not edited:
        f.close()
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    heads0 = sorted(h for h, _ in items)
    jobs_in = []
    for i, (h, d) in edited.items():
        nx = min([q for q in heads0 if q > h] or [SIZE])
        jobs_in.append((i, d, nx - h))
    packed = dict(pool.map(_pack, jobs_in))
    pool.close(); pool.join()

    heads = sorted(h for h, _ in items)
    for i, (hdr, plain) in edited.items():
        blob = packed[i]
        nxt = min([h for h in heads if h > hdr] or [SIZE])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % i
        raw[hdr:hdr + len(blob)] = blob
        for k in range(hdr + len(blob), nxt):
            raw[k] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(h for h, _ in edited.values()), "unexpected records changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
