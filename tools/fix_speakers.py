# -*- coding: utf-8 -*-
"""Fix rows whose speaker name disagrees with the rest of the game.

Found by pairing every dialogue row against the japanese at the same offset
and grouping by the JAPANESE speaker. A japanese name that maps to more than
one english name is either two characters sharing a name, or an error - and
the shape tells you which: 3,427 rows render $n as "$n" and four render it as
"Fudo".

The two that matter most are not spelling at all:

    $n   -> "Fudo" x4, "Sandman" x3, "Apollo" x3
        $n is the PLAYER-NAME MACRO. Replacing it with a literal name means
        whatever the player called themselves shows as somebody else.

    頭翅 -> "Zushi" x126, "Head-Wing" x9
        A name translated literally. 頭翅 is a person.

This normalises a minority spelling onto the majority the project already
uses. That is NOT name selection - the majority IS the project's choice, made
against the wiki elsewhere; this only stops one row disagreeing with 300. A
minority is only touched when the majority outnumbers it at least 5 to 1, so
two characters who genuinely share a japanese name are left alone.

Usage: fix_speakers.py <iso> [--dry-run]
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from fix_popup_wrap import sstrings

SEC, LBA, SIZE, BASE = 2048, 1651029, 3910128, 0x7566F0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATIO = 5           # majority must outnumber the minority by this much
LITERAL = {"Head-Wing", "Sound-Wing"}   # a name that was translated as words
MAXMINOR = 12       # and the minority must be small in absolute terms


def main():
    iso = sys.argv[1]
    dry = "--dry-run" in sys.argv
    f = open(iso, "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    f.close()
    recs = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(bytearray(
        open(os.path.join(ROOT, "extracted", "DATA_STAGE.BIN"), "rb").read()))

    pairs = collections.defaultdict(collections.Counter)
    rowsof = collections.defaultdict(list)
    for ri, (_h, p) in enumerate(recs):
        if p is None:
            continue
        ja = dict(sstrings(bytes(jp[ri][1]))) if ri < len(jp) and jp[ri][1] is not None else {}
        for off, s in sstrings(bytes(p)):
            if b"\n" not in s or len(s) > 220:
                continue
            j = ja.get(off)
            if not j or b"\n" not in j:
                continue
            try:
                e = s.decode("cp932"); t = j.decode("cp932")
            except UnicodeDecodeError:
                continue
            js, es = t.partition("\n")[0], e.partition("\n")[0]
            pairs[js][es] += 1
            rowsof[(js, es)].append((ri, off))

    fixes, skipped = [], []
    for js, ens in pairs.items():
        if len(ens) < 2:
            continue
        main_en, mn = ens.most_common(1)[0]
        for e, n in ens.items():
            if e == main_en or n > MAXMINOR or mn < n * RATIO:
                continue
            # Only normalise what is clearly ONE name spelled two ways, or a
            # macro, or a name that was translated literally. Two genuinely
            # different names (夜翅 as "Johannes" vs "Yashi") are a naming
            # question for the wiki, not something to settle by counting.
            import difflib
            same_name = difflib.SequenceMatcher(None, e.lower(),
                                                main_en.lower()).ratio() >= 0.55
            if not (same_name or main_en == "$n" or e in LITERAL):
                skipped.append((js, e, main_en, n))
                continue
            fixes.append((js, e, main_en, n))
    fixes.sort(key=lambda z: -z[3])
    total = sum(z[3] for z in fixes)
    print("speaker corrections: %d distinct, %d rows" % (len(fixes), total))
    for js, wrong, right, n in fixes[:20]:
        print("   %-12s %-14s -> %-14s x%d" % (js, wrong, right, n))

    if skipped:
        print("")
        print("NOT touched - genuinely different names, decide against the wiki:")
        for js, e, m, n in sorted(skipped, key=lambda z: -z[3])[:10]:
            print("   %-12s %-14s vs %-14s x%d" % (js, e, m, n))
    if dry:
        return 0

    edited = {}
    grew = 0
    for js, wrong, right, _n in fixes:
        for ri, off in rowsof[(js, wrong)]:
            p = bytearray(edited.get(ri, bytes(recs[ri][1])))
            ss = dict(sstrings(bytes(p)))
            old = ss.get(off)
            if old is None:
                continue
            try:
                t = old.decode("cp932")
            except UnicodeDecodeError:
                continue
            if t.partition("\n")[0] != wrong:
                continue
            new = (right + "\n" + t.partition("\n")[2]).encode("cp932")
            offs = sorted(ss)
            nxt = min([o for o in offs if o > off] or [len(p)])
            if len(new) + 1 > nxt - off:
                grew += 1
                continue                       # would not fit; leave it
            p[off:off + len(old)] = b"\x00" * len(old)
            p[off:off + len(new)] = new
            p[off + len(new)] = 0
            edited[ri] = bytes(p)
    print("records touched: %d   rows skipped for not fitting: %d"
          % (len(edited), grew))

    heads = sorted(h for h, _ in recs)
    for ri, plain in edited.items():
        hdr = recs[ri][0]
        nxt = min([h for h in heads if h > hdr] or [SIZE])
        blob = banlz.compress_record(plain)
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(plain)
        assert len(blob) <= nxt - hdr, "rec %d does not fit" % ri
        raw[hdr:hdr + len(blob)] = blob
        for k in range(hdr + len(blob), nxt):
            raw[k] = 0
    back = banlz.decompress_all(bytes(raw))
    for i in range(len(recs)):
        want = edited.get(i, bytes(recs[i][1]))
        assert bytes(back[i][1]) == want, "rec %d wrong" % i
    g = open(iso, "r+b"); g.seek(LBA * SEC); g.write(bytes(raw)); g.close()
    print("written and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
