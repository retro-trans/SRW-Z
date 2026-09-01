# -*- coding: utf-8 -*-
"""Re-wrap the DATA HELP panel text to the width the panel actually has.

THE PANEL IS 42 HALF-WIDTH COLUMNS AND DRAWS 4 LINES. Both measured, not
assumed. A ruler string written into a live field through PINE clipped after
"AAAAAAAAA|BBBBBBBBB|CCCCCCCCC|DDDDDDDDD|EE" - 42 columns - and all four of its
lines drew. The japanese in this pool never uses more than 4 lines either
(533 fields: 372 of 2, 98 of 3, 63 of 4), so 4 is the ceiling.

WHY SO MUCH OF IT OVERFLOWED. The rule used when this pool was translated was
"english character budget = japanese width in cells", which holds for the
description panels elsewhere but NOT here: the japanese in this panel is drawn
at roughly 8px per cell where our english is drawn at 13px per character, so
the japanese fits far more. That rule gave 58 columns where the panel has 42,
and left 271 of 1,111 fields clipping off the right edge.

HOW THE RE-WRAP KEEPS MEANING. A field is split into SEGMENTS at any line
break that follows a sentence end - "．", "。", "!" or "?" - because those
breaks are structure the translator put there (the barrier entry lists
"Nullify：..." and "Reduce：..." on their own lines, and reflowing them into
one blob would destroy that). Only the soft wraps inside a segment are redone.
A segment's own leading indent is preserved on its first line.

Nothing is written that does not fit: over 4 lines, over 42 columns, or over
its byte slot is REPORTED, never truncated. Those need shortening by hand,
which is editorial work and not this tool's business.

Output is analysis/compdata_raw.json, applied by apply_compdata_ui.py, which
writes it as raw cp932. It must NOT go through compdata_ui_left's encoder:
that maps '.' to a private half-width cell, correct for menu labels and wrong
for prose - it turns "this...!" into three extra bytes.

Usage: rewrap_help.py <iso> [--width N] [--max-lines N] [--apply]
"""
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "compdata_raw.json")
SECTOR = 2048
CD_LBA, CD_SPAN = 1823000, 400
LO, HI = 0x06c000, 0x080000          # the DATA HELP / description pool
NL = chr(10)
LAT = re.compile(r"[A-Za-z]{4}")
ENDS = (chr(0xFF0E), chr(0x3002), "!", "?", chr(0xFF01), chr(0xFF1F))


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def wrap(words, width, indent):
    """Greedy wrap. `indent` goes on the first line only."""
    out, line = [], indent
    for w in words:
        cand = (line + w) if not line.strip() else (line + " " + w)
        if line.strip() and cols(cand) > width:
            out.append(line)
            line = w
        else:
            line = cand
    if line:
        out.append(line)
    return out


def rewrap(text, width, maxlines):
    """Re-wrap to fit, preserving structure where the line budget allows.

    First choice keeps sentence-end breaks, because they are usually the
    translator's structure - the barrier entry lists "Nullify：" and "Reduce："
    as their own lines. But structure costs a line per item, and some fields
    hold less text than the panel fits yet still overflow purely from those
    breaks (0x072838: 143 columns of content spread over 6 lines). When keeping
    them does not fit, the whole field is reflowed as one paragraph: a page
    that reads as a block is worse than one that reads as a list, and better
    than one that runs off the edge of the screen.
    """
    kept = _rewrap_segments(text, width)
    if len(kept.split(NL)) <= maxlines:
        return kept
    first = text.split(NL)[0]
    indent = first[:len(first) - len(first.lstrip(" "))]
    words = " ".join(l.strip() for l in text.split(NL)).split()
    return NL.join(wrap(words, width, indent)) if words else kept


def _rewrap_segments(text, width):
    """Re-wrap soft wraps only, keeping sentence-end breaks as segments."""
    lines = text.split(NL)
    segs, cur = [], [lines[0]]
    for prev, ln in zip(lines, lines[1:]):
        if prev.rstrip().endswith(ENDS):
            segs.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    segs.append(cur)
    out = []
    for seg in segs:
        indent = seg[0][:len(seg[0]) - len(seg[0].lstrip(" "))]
        words = " ".join(l.strip() for l in seg).split()
        if not words:
            out.append("")
            continue
        out.extend(wrap(words, width, indent))
    return NL.join(out)


def main():
    iso = sys.argv[1]
    width = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 42
    maxl = int(sys.argv[sys.argv.index("--max-lines") + 1]) if "--max-lines" in sys.argv else 4

    f = open(iso, "rb")
    f.seek(CD_LBA * SECTOR)
    d = banlz.decompress_record(f.read(CD_SPAN * SECTOR), 0)[0]
    f.close()
    d = bytes(d)
    guard = set()
    ent = pool.entries(bytearray(d))
    for x in pool.stray_pointers_on_a_stride(bytearray(d), [s for s, _t, _k in ent]):
        guard.add(x[1] if isinstance(x, (tuple, list)) else x)

    p, fixes, refused, untouched = LO, {}, [], 0
    while p < HI:
        z = d.find(b"\x00", p)
        if z < 0:
            break
        if z > p + 8:
            try:
                s = d[p:z].decode("cp932")
            except UnicodeDecodeError:
                s = None
            if s and LAT.search(s):
                k = z
                while k < len(d) and d[k] == 0:
                    k += 1
                slot = k - p
                if any(cols(l) > width for l in s.split(NL)):
                    new = rewrap(s, width, maxl)
                    nb = new.encode("cp932", "replace")
                    why = None
                    if any(p <= g < p + len(nb) + 1 for g in guard):
                        why = "a pointer targets this slot"
                    elif len(new.split(NL)) > maxl:
                        why = "%d lines after wrapping, panel draws %d" % (
                            len(new.split(NL)), maxl)
                    elif max(cols(l) for l in new.split(NL)) > width:
                        why = "a word is wider than %d columns" % width
                    elif len(nb) >= slot:
                        why = "needs %d bytes, slot holds %d" % (len(nb) + 1, slot)
                    if why:
                        refused.append((p, why, s))
                    else:
                        fixes["0x%06x" % p] = [s, new]
                else:
                    untouched += 1
        while z < len(d) and d[z] == 0:
            z += 1
        p = z

    print("panel %d columns x %d lines" % (width, maxl))
    print("already inside the panel : %d" % untouched)
    print("re-wrapped               : %d" % len(fixes))
    print("REFUSED                  : %d" % len(refused))
    for off, why, s in refused:
        print("   %#08x  %s" % (off, why))
        print("      %r" % s.replace(NL, " | ")[:66])
    io.open(OUT, "w", encoding="utf-8", newline=NL).write(
        json.dumps(fixes, ensure_ascii=False, indent=1))
    print()
    print("wrote %s - apply with apply_compdata_ui.py" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
