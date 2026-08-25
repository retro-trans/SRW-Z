# -*- coding: utf-8 -*-
"""Re-wrap dialogue whose $ placeholders overflow the box once expanded.

THE BUG
    Dialogue carries runtime placeholders for the protagonist's name. The
    wrapper measured the TOKEN, not what it expands to, so a line could sit at
    a comfortable 30 columns in the data and render at 42:

        「This is $F of Glory Star. We      stored 30 columns
        「This is Setsuko・Ohara of Glory    rendered 42 -> clipped

    Reported from a screenshot where Setsuko's self-introduction ran off the
    right edge of the box; 148 strings are affected game-wide.

EXPANSIONS (columns, worst case over both protagonists)
    $F  14   full name      "Setsuko・Ohara" (Rand・Travis is 12)
    $n   7   short name     "Setsuko"        (Rand is 4)
    $f   7   given name
    $l   6   surname        "Travis" / "Ohara"
    $c   -   NOT handled: the squad name is player-entered, so it has no
             bound. The Japanese script has the same exposure.

The re-wrap is BYTE-NEUTRAL - only ' ' and '\n' are exchanged - so no string
moves and nothing needs repointing. Strings that cannot fit the 3-line box
even after re-wrapping are reported, not touched; they need shorter wording.

Usage: fix_placeholder_wrap.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES, strings

EXPAND = {"$F": "Setsuko\u30fbOhara", "$n": "Setsuko", "$f": "Setsuko",
          "$l": "Travis"}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return cols(s)


def wrap(flat):
    toks, lines, cur = flat.split(" "), [], []
    for t in toks:
        if cur and ecols(" ".join(cur + [t])) > WIDTH:
            lines.append(cur)
            cur = [t]
        else:
            cur = cur + [t]
    if cur:
        lines.append(cur)
    return [" ".join(l) for l in lines]


def fix_record(rec):
    d = bytearray(rec)
    n, hard = 0, []
    for s, e in strings(bytes(rec)):
        seg = bytes(d[s:e])
        if not any(k.encode() in seg for k in EXPAND):
            continue
        try:
            t = seg.decode("cp932")
        except UnicodeDecodeError:
            continue
        parts = t.split("\n")
        if len(parts) < 2:
            continue
        name, body = parts[0], parts[1:]
        if not any(ecols(l) > WIDTH for l in body):
            continue
        new = wrap(" ".join(body))
        if len(new) > MAXLINES or any(ecols(l) > WIDTH for l in new):
            hard.append((s, len(new), " / ".join(body)))
            continue
        nt = "\n".join([name] + new)
        nb = nt.encode("cp932")
        assert len(nb) == len(seg), "not byte-neutral"
        d[s:s + len(nb)] = nb
        n += 1
    return (bytes(d), n, hard) if n else (None, 0, hard)


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

    edited, total, hard = {}, 0, []
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        new, n, hh = fix_record(bytes(dec))
        for h in hh:
            hard.append((idx,) + h)
        if new is not None:
            edited[idx] = (hdr, new)
            total += n
    print("re-wrapped %d strings in %d records" % (total, len(edited)))
    print("cannot fit 3 lines even re-wrapped: %d" % len(hard))
    for h in hard:
        print("   rec %-4d @%-7d %d lines | %s" % (h[0], h[1], h[2], h[3][:80]))
    if dry or not edited:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    packed = dict(pool.map(_compress, [(i, d) for i, (h, d) in edited.items()]))
    pool.close(); pool.join()

    for idx, (hdr, plain) in edited.items():
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(h for h, _ in edited.values()), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
