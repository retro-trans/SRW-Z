# -*- coding: utf-8 -*-
"""Restore glossary links the English script dropped.

Audit: the Japanese marks 131 links; ours had 98. Comparing each JP string
against the English at the same offset found 27 JP links with no marker on our
side. They fall into three groups:

  * 13 in record 203 (Amuro and Kamille trading SRW trivia) point at オルファン,
    バルマー戦役 and 金田伊功 - terms with NO keyword entry anywhere. These stay
    unlinked: a link with no entry is a DEAD link, and a dead link crashes.
  * 10 are restored here, listed below.
  * 4 are deliberately skipped:
      Side ３ / Evidence ０１  - the entry names carry FULLWIDTH digits (the bank
          is menu-drawn, where ASCII 0x2E-0x3D are control codes), and a link
          must match the entry exactly, so linking would drag fullwidth digits
          into dialogue that otherwise uses half-width.
      PLANT Supreme Council Chairman - 30 chars, so 《...》 is 34 columns: the
          entire box width, leaving no room for the sentence around it.
  (ゲンガナム was a real mistranslation - the bank said "Gendarme" for the
  Turn A Gundam Moon city whose own description credits the "Ghingnham
  family". fix_ghingnham.py renamed the entry, so that link is restored here.)

Several lines had the term present but split across a line break, which also
breaks the link (Rau Le Creuset, Summer of Love); those are re-wrapped so the
term stays whole. Others paraphrased the term and are restored to the entry's
exact name ("Orb Defense" -> "Battle of Orb", "Space Science Lab" ->
"Space Science Laboratory", "Siberia Railway" -> "Siberian Railway",
"<Wheels>" -> "《Vodarac Wheel》s", "ref-board" -> "《Ref》").

Usage: relink_missing.py <iso> [--dry-run]
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

NEW = {
 (1, 38608):   (u"Denzel", Q1+u"Listen, Ensign. We are '"+O+u"Glory Star"+C+u"'... chosen for a mission that matters."+Q2),
 (82, 54352):  (u"Sara",   Q1+u"Cause the rock here is that "+O+u"Scub Coral"+C+u" stuff?"+Q2),
 (2, 67856):   (u"Durandal", Q1+u"...Halting military use of "+O+u"Orb"+C+u" technology and people that left in the last war?"+Q2),
 (2, 71152):   (u"Durandal", Q1+u"During the "+O+u"Battle of Orb"+C+u", the PLANTs took in the refugees of Orb."+Q2),
 (5, 24656):   (u"Hikaru", Q1+u"I keep signaling the "+O+u"Space Science Laboratory"+C+u", but no response."+Q2),
 (14, 35760):  (u"Adette", Q1+O+u"Siberian Railway"+C+u" guard. Where's Gainer?"+Q2),
 (25, 90816):  (u"$n",     Q1+u"You do "+O+u"Ref"+C+u" too, Renton?"+Q2),
 (25, 114048): (u"Bright", Q1+u"Now I understand why Chairman Durandal fears a second "+O+u"Summer of Love"+C+u"."+Q2),
 (89, 14256):  (u"Renton", Q1+u"So many "+O+u"Vodarac Wheel"+C+u"s.. Where did you get all these!?"+Q2),
 (135, 135952):(u"Ray",    Q1+u"I'm a clone. Just like "+O+u"Rau Le Creuset"+C+u", who died two years ago."+Q2),
 (127, 171552):(u"Dianna", Q1+u"Thank you, Captain Bright. I'll support your fight from the "+O+u"Ghingnham"+C+u"."+Q2),
}


GLUE = u""          # stands in for a space that must not break


def wrap_links(flat):
    """Wrap, but never break inside a 《term》 - the linker drops split terms."""
    glued = re.sub(O + u"(.*?)" + C,
                   lambda m: O + m.group(1).replace(u" ", GLUE) + C, flat)
    return [l.replace(GLUE, u" ") for l in wrap(glued)]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    built = {}
    for key, (name, flat) in sorted(NEW.items()):
        lines = wrap_links(flat)
        assert len(lines) <= MAXLINES, "%s: %d lines %s" % (key, len(lines), lines)
        for l in lines:
            assert ecols(l) <= WIDTH, "%s: %d cols %r" % (key, ecols(l), l)
        # a link must not straddle a line break or the game drops it
        for l in lines:
            assert l.count(O) == l.count(C), "%s: link split across lines: %r" % (key, l)
        built[key] = u"\n".join([name] + lines)
    print("all %d rewrites fit %dx%d with links intact" % (len(built), MAXLINES, WIDTH))

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
        assert len(nb) < k - off, "rec %d @%d: %d bytes > slot %d" % (idx, off, len(nb), k - off)
        b[off:k] = nb + b"\x00" * (k - off - len(nb))
        print("rec %-4d @%-7d %3d bytes / slot %d" % (idx, off, len(nb), k - off))
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
