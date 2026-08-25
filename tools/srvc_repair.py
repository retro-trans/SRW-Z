# -*- coding: utf-8 -*-
"""Normalise translated battle lines to the glyphs the font actually has.

The half-width atlas covers exactly 69 characters - . " ' ! , - ? plus 0-9 A-Z
a-z - and SADV gives the fullwidth space the same 13px advance, so space counts
as half-width too. Anything else still DRAWS, but as a native fullwidth glyph:
double width, visibly taller/wider than its neighbours, and it silently eats
twice its share of the 48-column line budget.

The model keeps this rule ~99.5% of the time and the strays are all mechanical
(~ from the Japanese ～, an occasional : or %), so they are rewritten here
rather than paid for again at the API.

Usage: srvc_repair.py [--write]      (default: report only)
"""
import collections
import io
import json
import os
import re
import sys

WORK = r"E:\Projects\SRW Z\_work"
OK = set(" .\"'!,-?0123456789"
         "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
MAXCOL = 48

# ～ marks drawn-out speech in Japanese and has no English equivalent worth a
# glyph; a colon is always droppable in a shouted line; the rest are spelled.
SUBS = [("~", ""), (":", ""), (";", ","), ("%", " percent"),
        ("(", ""), (")", ""), ("/", " "), ("*", ""), ("&", " and "),
        ("+", " plus "), ("=", ""), ("#", ""), ("@", " at "), ("_", " "),
        ("[", ""), ("]", ""), ("{", ""), ("}", ""), ("<", ""), (">", ""),
        ("|", " "), ("\\", ""), ("^", ""), ("`", "'"), ("$", "")]


def fix(v):
    parts = v.split("\\n")
    out = []
    for p in parts:
        for a, b in SUBS:
            if a in p:
                p = p.replace(a, b)
        p = "".join(c for c in p if c in OK)
        p = re.sub(r"\s{2,}", " ", p).strip()
        out.append(p)
    return "\\n".join(x for x in out if x)


def main():
    write = "--write" in sys.argv
    p = os.path.join(WORK, "analysis", "srvc_en.json")
    en = json.load(io.open(p, encoding="utf-8"))

    changed, wide, empty = {}, [], []
    offend = collections.Counter()
    for k, v in en.items():
        offend.update(c for c in v.replace("\\n", "") if c not in OK)
        nv = fix(v)
        if nv != v:
            changed[k] = (v, nv)
        if not nv:
            empty.append(k)
        elif max(len(x) for x in nv.split("\\n")) > MAXCOL:
            wide.append(k)

    print("entries %s | rewritten %s | over %d cols %d | emptied %d"
          % ("{:,}".format(len(en)), "{:,}".format(len(changed)),
             MAXCOL, len(wide), len(empty)))
    if offend:
        print("unsupported chars: " + ", ".join(
            "%s x%d" % (repr(c)[1:-1], n) for c, n in offend.most_common(12)))
    for k, (a, b) in list(changed.items())[:10]:
        print("   %-6s %-44s -> %s" % (k, a[:42], b))
    for k in wide[:5]:
        print("   WIDE %s %s" % (k, en[k]))

    if write and changed:
        for k, (_, b) in changed.items():
            if b:
                en[k] = b
            else:
                del en[k]           # nothing left: let it stay Japanese
        json.dump(en, io.open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("wrote %s (%s entries)" % (p, "{:,}".format(len(en))))
    elif changed:
        print("(report only; pass --write to apply)")


if __name__ == "__main__":
    main()
