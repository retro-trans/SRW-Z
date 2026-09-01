# -*- coding: utf-8 -*-
"""Render a rec6 section as it will appear on screen, to eyeball the layout.

Draws the runs onto a character grid at their real pixel positions, so a line
that overruns the panel or collides with the one below is visible here rather
than only on the console.

Usage: nisv_rec6_preview.py <iso> <section> [<section>...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nisv_rec6
import nisv_rec6_para as para
import nisv_rec6_apply as ap

CELL = 12                       # a half-width cell, in pixels


def render(sec):
    """Lay the runs out on a text grid at their real pixel positions."""
    rows = {}
    for r in sec.runs:
        rows.setdefault(r.y, []).append(r)
    out = []
    for y in sorted(rows):
        line, pen = [], 0
        for r in sorted(rows[y], key=lambda r: r.x):
            while pen + CELL <= r.x:      # pad by pixels, not by characters
                line.append(" ")
                pen += CELL
            line.append(r.text)
            pen = r.x + para.px(r.text)
        out.append((y, "".join(line)))
    return out


def main():
    iso = sys.argv[1]
    want = [int(a) for a in sys.argv[2:]]
    en = ap.load_en()
    b = ap.nisv_rec6 and None
    import banlz
    f = open(iso, "rb")
    f.seek(ap.LBA * 2048)
    items = banlz.decompress_all(f.read(ap.SECT * 2048))
    f.close()
    data = bytes(items[6][1])
    secs, _ = nisv_rec6.parse(data)
    for s in secs:
        if s.index not in want or s.runs is None:
            continue
        ap.translate_section(s, en, [0, 0])
        print("=" * 72)
        print("section %d   (%d runs, %d bytes, max y %d)"
              % (s.index, len(s.runs), len(s.body()) + 2,
                 max(r.y for r in s.runs)))
        print("=" * 72)
        for y, text in render(s):
            wide = max((r.x + para.px(r.text)) for r in s.runs if r.y == y)
            flag = "  <<OVER %d" % wide if wide > para.RIGHT else ""
            print("%4d |%s%s" % (y, text, flag))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
