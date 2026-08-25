# -*- coding: utf-8 -*-
"""Scan every STAGE record for defects a PLAYER would see on screen.

Reads the image directly, so it works on all 205 records - not just the 26 with
exports, and not dependent on the export pairing (which is ~30% wrong, see
analysis/review/EXPORT_TRUST.md).

Checks, in rough order of how bad they look in play:

  overflow_lines  body has more than 3 lines           -> text runs out of the box
  overflow_cols   a body line exceeds 34 columns       -> text runs off the edge
  untranslated    latin-free japanese prose in dialogue-> untranslated line
  bad_placeholder $ followed by an unknown letter      -> prints literally
  literal_escape  a literal backslash-n / backslash-t  -> prints as characters
  empty_body      speaker line but no body             -> blank box
  mojibake        private-use or replacement chars     -> garbage glyph

Placeholders EXPAND at runtime, so widths are measured expanded: $n/$f 7 cols,
$F 14, $l 6. $c is a player-entered squad name and is unbounded - rows using it
are reported separately, not as overflow.

Usage: scan_visible_defects.py <iso> [--kind <name>] [--limit N]
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

KAGI = u"「"
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
KNOWN_PH = set("nfFlc")
BS = chr(92)


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def jp_chars(s):
    return len(re.findall(u"[぀-ヿ一-鿿]", s))


def scan(iso):
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()
    found = collections.defaultdict(list)
    rows = 0
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        buf = bytes(data)
        i = 0
        while i < len(buf):
            j = buf.find(b"\x00", i)
            if j == -1:
                j = len(buf)
            seg = buf[i:j]
            if len(seg) > 4:
                try:
                    s = seg.decode("cp932")
                except Exception:
                    i = j + 1
                    continue
                if KAGI in s:
                    rows += 1
                    check(idx, i, s, found)
            i = j + 1
    return rows, found


def check(idx, off, s, found):
    lines = s.split("\n")
    body = lines[1:]
    rec = (idx, off, s.replace("\n", " | ")[:70])

    if not body:
        # INLINE format: name and quote on ONE line, no newline. Legitimate -
        # rec203 'Bright「Let's give it our all.」' is correct, not empty.
        if s.index(KAGI) > 0:
            return
        found["empty_body"].append(rec)
        return
    if not "".join(body).strip():
        found["empty_body"].append(rec)
        return
    if len(body) > MAXLINES:
        found["overflow_lines"].append(rec)
    has_c = "$c" in s
    for b in body:
        if ecols(b) > WIDTH:
            found["overflow_cols_squadname" if has_c else "overflow_cols"].append(rec)
            break
    if BS + "n" in s or BS + "t" in s:
        found["literal_escape"].append(rec)
    for m in re.finditer(r"\$(.)", s):
        if m.group(1) not in KNOWN_PH:
            found["bad_placeholder"].append(rec)
            break
    if re.search(u"[-�]", s):
        found["mojibake"].append(rec)
    # a dialogue body that is still japanese prose with no latin at all
    txt = "".join(body)
    if jp_chars(txt) >= 6 and not re.search(r"[A-Za-z]", txt):
        found["untranslated"].append(rec)


def main():
    iso = sys.argv[1]
    kind = None
    if "--kind" in sys.argv:
        kind = sys.argv[sys.argv.index("--kind") + 1]
    limit = 12
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    rows, found = scan(iso)
    print("dialogue rows scanned: %d\n" % rows)
    order = ["overflow_lines", "overflow_cols", "untranslated", "bad_placeholder",
             "literal_escape", "empty_body", "mojibake", "overflow_cols_squadname"]
    for k in order:
        v = found.get(k, [])
        print("  %-24s %d" % (k, len(v)))
    if kind:
        v = found.get(kind, [])
        print("\n=== %s (%d) ===" % (kind, len(v)))
        byrec = collections.Counter(r[0] for r in v)
        print("worst records: %s" % byrec.most_common(8))
        for idx, off, txt in v[:limit]:
            print("  rec%-4d off=%-7d %s" % (idx, off, txt))


if __name__ == "__main__":
    main()
