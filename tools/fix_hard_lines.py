# -*- coding: utf-8 -*-
"""Shorten the 8 dialogue lines that cannot fit the box once $ expands.

fix_placeholder_wrap.py re-wraps lines whose placeholders overflow, but 8
strings still needed 4 lines in a 3-line box, so they need fewer words rather
than different breaks. The wording below is supplied flat; this script wraps it
with the same expansion-aware wrapper and refuses anything that does not fit.

Also folded in: "lift-boarding" -> "reffing" in Sara's line, matching リフ =
Ref used by the skill name and the glossary entry.

Usage: fix_hard_lines.py <iso>
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from fix_placeholder_wrap import ecols, wrap
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

NEW = {
    (9, 44512):    (u"$n", u"(If the colony falls, many kids here will lose their parents too. Just like me, that day...)"),
    (25, 93776):   (u"Renton", u"\u300cIt's fine, $f. I can ref-board tomorrow, and staying home just means gramps nagging.\u300d"),
    (57, 53552):   (u"Amuro", u"\u300cAsakim's reason for targeting $n... Virgola must be involved somehow.\u300d"),
    (57, 53744):   (u"Quattro", u"\u300cVirgola, the Gunnery Carver.. and $n. The key may lie in what links them.\u300d"),
    (107, 136848): (u"Eiji", u"\u300c$n, Tsugumi, Maria, Sochie, Fa, Keiko, Emma, Sara, Kouji, Jiron... everyone's crying!\u300d"),
    (107, 138912): (u"Eiji", u"\u300cShinn and Kamille suffering, fighting Garrod and $n... the battle to save this world...\u300d"),
    (116, 22384):  (u"Sara", u"\u300cYou had cake with $n, lizard with Jiron and Apollo, Holland taught you reffing...\u300d"),
    (129, 29024):  (u"Sara", u"\u300cYou had cake with $n, lizard with Jiron and Apollo, Holland taught you reffing...\u300d"),
}


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    built = {}
    for key, (name, flat) in sorted(NEW.items()):
        lines = wrap(flat)
        assert len(lines) <= MAXLINES, "%s: %d lines: %s" % (key, len(lines), lines)
        for l in lines:
            assert ecols(l) <= WIDTH, "%s: %d cols %r" % (key, ecols(l), l)
        built[key] = u"\n".join([name] + lines)
        print("%-14s %d lines, widest %d" % (str(key), len(lines),
                                             max(ecols(l) for l in lines)))
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
        assert len(nb) < k - off, "rec %d: %d bytes > slot %d" % (idx, len(nb), k - off)
        print("rec %-4d @%-7d %3d->%3d bytes" % (idx, off, e - off, len(nb)))
        b[off:k] = nb + b"\x00" * (k - off - len(nb))

    jobs = max(1, (os.cpu_count() or 4) - 2)
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
    print("\n%d lines rewritten in %d records" % (len(built), len(recs)))


if __name__ == "__main__":
    main()
