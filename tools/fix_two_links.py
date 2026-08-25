# -*- coding: utf-8 -*-
"""Two link repairs found by the post-pass audit.

1. rec 127: 《Ghingnham》 restored, now that fix_ghingnham.py renamed the bank
   entry from "Gendarme" to match the dialogue.

2. rec 5: a link that was BOTH split across a line break AND wrong - the text
   said "Second Battle of Jachin Due" while the entry is "２nd Battle of Jachin
   Due" (fullwidth ２, because the bank is menu-drawn). It could never resolve.
   The markers are removed rather than the digit style dragged into dialogue,
   matching how the other fullwidth-digit entries are handled.

   Both audits had missed it: the dead-link check extracts 《...》 with a regex
   where '.' does not match a newline, so a split link is invisible to it.

Usage: fix_two_links.py <iso>
"""
import multiprocessing
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from fix_placeholder_wrap import ecols, wrap
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

Q1, Q2 = u"\u300c", u"\u300d"
O, C = u"\u300a", u"\u300b"
GLUE = u"\ue000"

NEW = {
 (127, 171552): (u"Dianna", Q1+u"Thank you, Captain Bright. I'll support your fight from the "+O+u"Ghingnham"+C+u"."+Q2),
 (5, 35664):    (u"Kappei", Q1+u"The Second Battle of Jachin Due, right? That fight was amazing, I hear!"+Q2),
}


def wrap_links(flat):
    glued = re.sub(O + u"(.*?)" + C,
                   lambda m: O + m.group(1).replace(u" ", GLUE) + C, flat)
    return [l.replace(GLUE, u" ") for l in wrap(glued)]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    built = {}
    for key, (name, flat) in sorted(NEW.items()):
        lines = wrap_links(flat)
        assert len(lines) <= MAXLINES, "%s: %d lines" % (key, len(lines))
        for l in lines:
            assert ecols(l) <= WIDTH, "%s: %d cols %r" % (key, ecols(l), l)
            assert l.count(O) == l.count(C), "%s: link split: %r" % (key, l)
        built[key] = u"\n".join([name] + lines)
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    recs = {}
    for (idx, off), text in sorted(built.items()):
        b = recs.setdefault(idx, bytearray(items[idx][1]))
        e = off
        while b[e] != 0:
            e += 1
        k = e
        while k < len(b) and b[k] == 0:
            k += 1
        nb = text.encode("cp932")
        assert len(nb) < k - off, "rec %d: %d > slot %d" % (idx, len(nb), k - off)
        b[off:k] = nb + b"\x00" * (k - off - len(nb))
        print("rec %-4d @%-7d %3d bytes / slot %d" % (idx, off, len(nb), k - off))
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
    assert set(changed) <= set(items[i][0] for i in recs), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed" % len(changed))


if __name__ == "__main__":
    main()
