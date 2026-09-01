# -*- coding: utf-8 -*-
"""Translate rec6's "see also" cross-reference lines from the term table.

A cross-reference line is nothing but glossary terms in fullwidth angle
brackets, separated by fullwidth spaces, sometimes over several display lines:

    <Spirits>  <Pilot Training>  <Unit Upgrade>
    <Parts>  <Target Size>  <Terrain>

So they do not need translating by hand - they need the SAME english the menus
use, which is what nisv_terms.py collects. This renders each line from that
table.

ALL OR NOTHING, per line. If any term in a line has no entry, the whole line is
left japanese rather than shipped half-translated: a list reading
"<Spirits>  <援護防御>" is worse than one that is honestly still japanese, and
it would hide the missing term from the next pass.

BRACKETS. The japanese wraps each term in fullwidth angle brackets, and the
obvious english is to keep them - but they cost 2 bytes each while an english
term is LONGER in characters than the kanji it replaces (小隊攻撃 is 8 bytes,
"Squad Atk" is 9), so six lines overflowed their field on the first attempt.

ASCII square brackets are used instead: 0x5B and 0x5D are outside the
0x2E-0x3D control range, they read naturally in english, and they save 2 bytes
per term. The separator likewise drops from one ideographic space to two ASCII
ones - same 2 bytes, clearer at this size. ASCII '<' is NOT an option: 0x3C is
a control code on this path.

Usage: nisv_xref_en.py <iso>      writes analysis/nisv_rec6_xref.json
"""
import hashlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from nisv_extract import strings, LBA, SECTORS
from nisv_terms import TERMS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "nisv_rec6_xref.json")
OPEN, CLOSE, WSP, NL = u"\uff1c", u"\uff1e", u"\u3000", chr(10)
EOPEN, ECLOSE, ESEP = u"[", u"]", u"  "
TERM = re.compile(OPEN + u"([^" + CLOSE + u"]+)" + CLOSE)


def render(line, sep=ESEP):
    """One display line of terms -> english, or None if a term is unknown."""
    found = TERM.findall(line)
    if not found:
        return None
    rest = TERM.sub(u"", line).replace(WSP, u"").strip()
    if rest:                       # prose mixed in - not a pure list
        return None
    out = []
    for t in found:
        if t not in TERMS:
            return None
        out.append(EOPEN + TERMS[t] + ECLOSE)
    return sep.join(out)


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(LBA * 2048)
    recs = banlz.decompress_all(f.read(SECTORS * 2048))
    f.close()
    b = bytes(recs[6][1])
    rows, done, blocked = [], 0, {}
    for off, t, ln, room in strings(b):
        if OPEN not in t:
            continue
        lines = t.split(NL)
        outl = [render(l) for l in lines]
        if any(o is None for o in outl):
            for l in lines:
                for term in TERM.findall(l):
                    if term not in TERMS:
                        blocked[term] = blocked.get(term, 0) + 1
            continue
        new = NL.join(outl)
        if len(new.encode("cp932")) >= room:
            # Fall back to a single space between terms before giving up.
            # Costs nothing in meaning and rescues lines that miss by one
            # or two bytes - which several do, because an english term is
            # longer in characters than the kanji it replaces.
            tight = NL.join(render(l, u" ") for l in lines)
            if len(tight.encode("cp932")) < room:
                new = tight
        if len(new.encode("cp932")) >= room:
            blocked["(too long) %s" % new[:24]] = 1
            continue
        rows.append([hashlib.sha1(t.encode("cp932", "ignore")).hexdigest()[:16],
                     new])
        done += 1
    # ACCUMULATE. Once a line is applied it is no longer japanese in the
    # image, so a later run cannot see it and would drop it from this file
    # - the record of what was translated would shrink every pass.
    seen = {}
    if os.path.exists(OUT):
        for k, v in json.load(io.open(OUT, encoding="utf-8")):
            seen[k] = v
    before = len(seen)
    for k, v in rows:
        seen[k] = v
    rows = [[k, v] for k, v in sorted(seen.items())]
    print("%d line(s) already on file, %d new" % (before, len(rows) - before))
    print("cross-reference lines rendered: %d" % len(rows))
    print("lines left japanese for want of a term: %d distinct term(s)"
          % len(blocked))
    for t, n in sorted(blocked.items(), key=lambda x: -x[1])[:18]:
        print("   %-22s x%d" % (t, n))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
