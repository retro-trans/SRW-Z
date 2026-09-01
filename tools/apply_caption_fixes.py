# -*- coding: utf-8 -*-
"""Apply proofread battle-caption rewrites in place, both copies.

WHY NOT srvc_apply. The designed path rebuilds SRVC from analysis/srvc_en.json,
and that file does NOT contain the corrections made straight to the image since
the last rebuild - srvc_line_fixes, fix_srvc_names, patch_srvc_polish,
fix_lowen_captions. Checked, not assumed: of the srvc_line_fixes replacements,
ZERO are present in srvc_en.json. Rebuilding would silently revert every one of
them, so proofreading is applied in place instead.

THE EXTENT, and why a longer line is still safe. srvc_apply pads each caption
out to the byte length of the japanese it replaced. Japanese is two bytes per
character and our english is roughly one, so nearly every field carries a run
of trailing spaces - and that run is spendable. A field is therefore

    <english bytes><trailing 0x20 ...>

and the replacement may use the whole run. The field START never moves, which
is the invariant that matters: voice-sync offsets are absolute. A replacement
too long for its run is REPORTED AND SKIPPED, never truncated - a caption cut
to fit is not the line the proofreader approved. This is the same rule
srvc_line_fixes.py uses, applied from a table instead of by hand.

BOTH COPIES. The caption strings exist twice - the pool the srvc toolchain
rewrites, and a second copy the toolchain never touched, which on 2026-08-31
turned out to be the one on screen. So this scans the WHOLE image and fixes
every occurrence.

Captions are drawn by the menu reader, so text is encoded with
patch.encode(mode="menuhw"): '.' and 0-9 become two-byte private glyphs.

Idempotent: a field already holding its replacement is counted and skipped.

Usage: apply_caption_fixes.py <iso> [--write]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "caption_fixes.json")
CHUNK = 64 * 1024 * 1024
SP = 0x20


def find_all_multi(f, needles):
    """One pass over the image for EVERY needle at once.

    A pass per needle meant 83 reads of a 4.5 GB image - 370 GB of IO for a few
    dozen small writes, and minutes of wall clock. The strings are searched
    together instead, so the file is read once."""
    hits = dict((n, []) for n in needles)
    longest = max(len(n) for n in needles)
    prev, base = b"", 0
    f.seek(0)
    while True:
        b = f.read(CHUNK)
        if not b:
            break
        buf = prev + b
        for n in needles:
            q = 0
            while True:
                q = buf.find(n, q)
                if q < 0:
                    break
                hits[n].append(base - len(prev) + q)
                q += 1
        prev = buf[-longest:]
        base += len(b)
    return hits


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    fixes = json.load(io.open(SRC, encoding="utf-8"))
    f = open(iso, "r+b" if write else "rb")
    applied = already = missing = toolong = 0
    skipped = []
    work = []
    for x in fixes:
        old = encode(x["was"], "menuhw")
        new = encode(x["text"], "menuhw")
        if old != new:
            work.append((x, old, new))
    hits = find_all_multi(f, [o for _x, o, _n in work]
                          + [n for _x, _o, n in work])

    def run_after(pos, n):
        """Spendable trailing-space run after a field body."""
        f.seek(pos + n)
        tail = f.read(64)
        r = 0
        while r < len(tail) and tail[r] == SP:
            r += 1
        return r

    for x, old, new in work:
        where = hits.get(old) or []
        if not where:
            if hits.get(new):
                already += 1
            else:
                missing += 1
                skipped.append((x, "not found in the image"))
            continue
        room = min(len(old) + run_after(h, len(old)) for h in where)
        if len(new) > room:
            toolong += 1
            skipped.append((x, "needs %d bytes, field holds %d"
                            % (len(new), room)))
            continue
        for h in where:
            extent = len(old) + run_after(h, len(old))
            if write:
                f.seek(h)
                f.write(new + b" " * (extent - len(new)))
        applied += 1
    f.close()
    print("%d rewrite(s) applied, %d already in place, %d too long, "
          "%d not found" % (applied, already, toolong, missing))
    for x, why in skipped[:20]:
        print("   SKIPPED %-16s %s" % (x["key"], why))
        print("      was %r" % x["was"][:60])
        print("      new %r" % x["text"][:60])
    if not write:
        print("(dry run - pass --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
