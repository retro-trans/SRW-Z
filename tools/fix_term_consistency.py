# -*- coding: utf-8 -*-
u"""Term drift found by re-reading stage 48 (rec111, all 883 rows).

The re-read of stage 48 found ~0.8% defects against 26% in the sonnet
range, and all but one were consistency rather than mistranslation. This
applies the ones that are settled; the two that need a ruling are left
alone and reported to the user instead.

Every replacement here is the SAME LENGTH OR SHORTER, so nothing grows,
nothing relocates and no pointer changes.

  Over Devil   -> Overdevil     glossary says Overdevil, and the disc
                                agrees 310 to 10. Not a majority vote -
                                [[naming-baseline-wiki]] - the glossary
                                is the record and the 10 are the drift.
  Garna Han    -> Garnahan      1 against 8, and "～Garnahan Gorge～"
  Generall     -> General       3 rows in rec41 against 17 elsewhere;
                                akurasu spells him Löwen General, and ö
                                is not representable in cp932
  silhouette   -> Silhouette    Silhouette Machine is a mecha class
  the new      -> the New       新連邦 / 新地球連邦 are proper nouns.
                                Case-only, so zero byte change. Applied
                                ONLY where the japanese actually holds
                                新連邦 or 新地球連邦, never to a row where
                                "new" is an ordinary adjective.

Plus one real mistranslation, the only one in 883 rows:

  「ヤーパンの天井のヒューズ・ガウリだな」
     was "You're Hughes Gauli, the Ceiling of Yapan"
     now "You're Hughes Gauli of Yapan's Ceiling"
  The appositive was misparsed - he is FROM Yapan's Ceiling, he is not
  the ceiling.

Usage: fix_term_consistency.py <iso> <jp-iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X
import fix_shadow_angels as S      # rewrap()

SEC, LBA, SIZE = 2048, 1651029, 3910128

# (english regex, replacement, japanese term that must be present or None)
SUBS = [
    (re.compile(r'Generall\b'), u'General', u'ゲネラール'),
    (re.compile(r'silhouette machine'), u'Silhouette Machine', u'シルエットマシン'),
    # \s+ so it also catches "new\nFederation" - the term wraps in 7 rows and
    # a literal-space pattern misses every one. Safe across a line break
    # because this is a CASE change only: same bytes, same wrapping.
    # "new Earth\nFederation" wraps between Earth and Federation too, so it
    # needs its own pattern; the general one requires "Earth Fed" contiguous.
    (re.compile(r'\bnew(\s+)Earth(\s+)Fed'), u'New\\1Earth\\2Fed', None),
    (re.compile(r'\bnew(\s+)(Fed|EF|Earth Fed)'), u'New\\1\\2', None),
]
NEWFED = (u'新連邦', u'新地球連邦')

# the one mistranslation, matched on flattened text
FIXES = [
    (111, u'Hughes Gauli, the Ceiling of Yapan',
     u'Hughes Gauli, the Ceiling of Yapan', u"Hughes Gauli of Yapan's Ceiling"),
]

# User rulings, 2026-09-09. Both were dead-heat inconsistencies the disc
# could not settle on its own: 准将 ran General 154 / Brigadier General 17,
# with both forms nine rows apart in one rec111 scene, and アーサーさん ran
# "Arthur-san" 3 / "Mr. Arthur" 3.
#
# These are applied by FLATTENING the body, substituting, then re-wrapping
# to the body's own width. "Brigadier General" wraps, and consuming the
# newline with a plain replace would leave an over-long line; re-wrapping
# keeps the box honest. Both replacements are shorter or equal, so no row
# can grow: "Brigadier General" -> "General" saves 10 bytes and
# "Arthur-san" -> "Mr. Arthur" is exactly the same length.
RULINGS = [
    # these two also WRAP, so they need the re-wrap path: consuming the
    # newline with a plain replace would leave an over-long line
    (re.compile(r'Over\s+Devil'), u'Overdevil', u'オーバーデビル'),
    (re.compile(r'Garna\s+Han'), u'Garnahan', u'ガルナハン'),
    (re.compile(r'Brigadier\s+General'), u'General', u'准将'),
    (re.compile(r'Brig\.\s*Gen\.'), u'General', u'准将'),
    # a THIRD form: bare "Brigadier Blex" / "Brigadier Edel" with no
    # "General" after it. 30 rows, invisible to the pattern above.
    (re.compile(r'Brigadier'), u'General', u'准将'),
    (re.compile(r'Arthur-san'), u'Mr. Arthur', u'アーサー'),
]


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    g = open(jpiso, "rb")
    g.seek(LBA * SEC)
    jp = [d for h, d in banlz.decompress_all(g.read(SIZE))
          if isinstance(h, int) and d is not None]
    g.close()

    touched, counts = {}, {}
    for rec, (h, d) in enumerate(live):
        jb = bytes(jp[rec])
        for ve, (vj, p) in EP.pair(bytes(d), jb).items():
            j, _ = EP.text_at(jb, vj)
            e, room = EP.text_at(bytes(d), ve)
            if not j or not e:
                continue
            new = e
            for rx, rep, jt in SUBS:
                if jt is not None and jt not in j:
                    continue
                if jt is None and not any(t in j for t in NEWFED):
                    continue
                # a term split across a line break is invisible to a raw
                # match; check the flattened form and rebuild if it hits
                if not rx.search(new) and rx.search(' '.join(new.split())):
                    print("  rec%-4d term spans a line break, SKIPPED: %r"
                          % (rec, ' '.join(new.split())[:56]))
                    continue
                n2 = rx.sub(rep, new)
                if n2 != new:
                    counts[rep] = counts.get(rep, 0) + 1
                    new = n2
            for frec, loc, old, rep in FIXES:
                if rec != frec or loc not in ' '.join(new.split()):
                    continue
                # the phrase wraps ("Ceiling of\nYapan"), so a raw replace
                # finds nothing while the flattened test passes - flatten,
                # replace, then re-wrap the body to its own width
                sp, sep, body = new.partition('\n')
                if not sep:
                    continue
                width = max(len(x) for x in body.split('\n'))
                flat = ' '.join(body.split()).replace(old, rep)
                n2 = sp + '\n' + S.rewrap(flat, width)
                if n2 != new:
                    counts[rep] = counts.get(rep, 0) + 1
                    new = n2
            # rulings: flatten, substitute, re-wrap to the body's own width
            hit = [(rx, rep) for rx, rep, jt in RULINGS
                   if jt in j and rx.search(' '.join(new.split()))]
            if hit:
                sp, sep, body = new.partition('\n')
                if sep:
                    width = max(len(x) for x in body.split('\n'))
                    flat = ' '.join(body.split())
                    for rx, rep in hit:
                        flat = rx.sub(rep, flat)
                        counts[rep] = counts.get(rep, 0) + 1
                    new = sp + '\n' + S.rewrap(flat, width)
                else:
                    for rx, rep in hit:
                        new = rx.sub(rep, new)
                        counts[rep] = counts.get(rep, 0) + 1
            if new == e:
                continue
            nb = new.encode("cp932")
            if len(nb) > room - 1:
                print("  rec%-4d %d B > budget %d, SKIPPED" % (rec, len(nb), room - 1))
                continue
            z = bytes(d).find(b"\x00", ve)
            d[ve:ve + len(nb)] = nb
            for x in range(ve + len(nb), max(z, ve + len(nb))):
                d[x] = 0
            d[ve + len(nb)] = 0
            touched[rec] = True
    print("")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("  %-34s %d" % (k, v))
    print("records touched: %d" % len(touched))
    if not touched or not write:
        if touched:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0
    for rec in sorted(touched):
        h = live[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(bytes(live[rec][1]))
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(bytes(live[rec][1]))
        assert len(blob) <= nxt - h, "rec%d over slot" % rec
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
