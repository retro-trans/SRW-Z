# -*- coding: utf-8 -*-
"""Find dialogue rows whose quoting is broken - the class the Zushi row is in.

Reported from a backlog screenshot 2026-08-26: Zushi's line rendered

    Zushi
    "As you

The stored row was `Zushi\n"As you` in a 48-byte slot - truncated mid-sentence,
with an ASCII double quote where the opening kagi should be. Japanese source was
`頭翅\n「御意…」`.

scan_visible_defects.py never caught it: the row has one line, is under 34
columns, has no literal escape and no Japanese left, so every existing check
passed. What is wrong is the QUOTING, so that is what this looks at.

  unbalanced   count of 「 != count of 」   -> a quote span was cut
  ascii_quote  body opens with ASCII " or '  -> wrong delimiter
  no_open      speaker line but body has no 「 and no ASCII quote
  truncated    unbalanced AND the slot has >= 8 spare bytes, i.e. it was cut
               short with room to spare, so it was a writer bug not a fit
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

OPEN, CLOSE = u"\u300c", u"\u300d"


def main():
    iso = sys.argv[1]
    kind = sys.argv[sys.argv.index("--kind") + 1] if "--kind" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 25
    f = open(iso, "rb"); f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE)); f.close()

    found = collections.defaultdict(list)
    rows = 0
    for idx, (hdr, data) in enumerate(items):
        if data is None: continue
        buf = bytes(data); i = 0
        while i < len(buf):
            j = buf.find(b"\x00", i)
            if j == -1: j = len(buf)
            seg = buf[i:j]
            if len(seg) > 4:
                try: s = seg.decode("cp932")
                except Exception:
                    i = j + 1; continue
                k = j
                while k < len(buf) and buf[k] == 0: k += 1
                if "\n" in s and (OPEN in s or '"' in s or "'" in s):
                    rows += 1
                    check(idx, i, s, k - i, j - i, found)
            i = j + 1

    print("quoted dialogue rows scanned: %d\n" % rows)
    for key in ("truncated", "unbalanced", "ascii_quote", "no_open"):
        print("  %-14s %d" % (key, len(found[key])))
    if kind:
        v = found[kind]
        print("\n=== %s (%d) ===" % (kind, len(v)))
        for idx, off, txt, slot, ln in v[:limit]:
            print("  rec%-4d off=%#08x len=%-4d slot=%-4d %r"
                  % (idx, off, ln, slot, txt))


def check(idx, off, s, slot, ln, found):
    body = s.split("\n", 1)[1] if "\n" in s else ""
    rec = (idx, off, s.replace("\n", " | ")[:76], slot, ln)
    nopen, nclose = s.count(OPEN), s.count(CLOSE)
    if nopen != nclose:
        found["unbalanced"].append(rec)
        if slot - ln >= 8:
            found["truncated"].append(rec)
    if body[:1] in ('"', "'"):
        found["ascii_quote"].append(rec)
    elif nopen == 0 and body:
        found["no_open"].append(rec)


if __name__ == "__main__":
    main()
