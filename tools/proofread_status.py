# -*- coding: utf-8 -*-
"""How many lines a human has actually proofread, counted rather than claimed.

Tracking this per STAGE does not work. A proofreader reads whatever the sheet
puts in front of them, stops mid-record, comes back to another one, and leaves
most rows untouched on purpose - "no change needed" is a valid verdict that
looks identical to "never read". So a per-stage tick box would be wrong within
a week and could only ever be a guess.

A LINE COUNT is a fact. Every row a proofreader touched carries their name in
the sheet's `by` column, so this counts:

    reviewed   rows where they entered anything - a rewrite, a status, a note
    rewritten  rows where they supplied replacement english

`reviewed` is the honest number for "a human has looked at this". `rewritten`
is the subset that changed the game. Both are worth showing: a proofreader who
reads 200 lines and changes 5 has done 200 lines of work, not 5.

Reads analysis/sheet_entries.json, which sheets_preserve.py writes straight
from the workbooks. Re-run sheets_preserve.py first for current numbers.

Usage: proofread_status.py [--md]
"""
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "sheet_entries.json")
# denominators: the whole worklist, so the share is not flattering
TOTAL_DIALOGUE = 68114
TOTAL_CAPTIONS = 19213


def collect():
    if not os.path.exists(SRC):
        raise SystemExit("no %s - run sheets_preserve.py first" % SRC)
    d = json.load(io.open(SRC, encoding="utf-8"))
    who = collections.defaultdict(
        lambda: {"dialogue": 0, "captions": 0, "rewritten": 0})
    for key, cells in d.items():
        proposed = cells[0] if cells else ""
        name = (cells[3] if len(cells) > 3 else "").strip() or "unattributed"
        kind = "captions" if key.startswith("b") else "dialogue"
        who[name][kind] += 1
        if proposed:
            who[name]["rewritten"] += 1
    return who


def main():
    who = collect()
    rows = sorted(who.items(), key=lambda kv: -(kv[1]["dialogue"] + kv[1]["captions"]))
    d_tot = sum(v["dialogue"] for _n, v in rows)
    c_tot = sum(v["captions"] for _n, v in rows)
    r_tot = sum(v["rewritten"] for _n, v in rows)
    if "--md" in sys.argv:
        print("| Proofreader | Dialogue lines | Battle lines | Rewritten |")
        print("|---|---|---|---|")
        for n, v in rows:
            print("| %s | %d | %d | %d |"
                  % (n, v["dialogue"], v["captions"], v["rewritten"]))
        print("| **Total** | **%d** | **%d** | **%d** |" % (d_tot, c_tot, r_tot))
        print()
        print("%d of %d dialogue lines (%.2f%%) and %d of %d battle lines "
              "(%.2f%%) have been read by a human."
              % (d_tot, TOTAL_DIALOGUE, 100.0 * d_tot / TOTAL_DIALOGUE,
                 c_tot, TOTAL_CAPTIONS, 100.0 * c_tot / TOTAL_CAPTIONS))
        return 0
    print("%-16s %9s %9s %10s" % ("proofreader", "dialogue", "battle", "rewritten"))
    for n, v in rows:
        print("%-16s %9d %9d %10d" % (n, v["dialogue"], v["captions"], v["rewritten"]))
    print("%-16s %9d %9d %10d" % ("TOTAL", d_tot, c_tot, r_tot))
    print()
    print("dialogue: %d of %d read by a human (%.2f%%)"
          % (d_tot, TOTAL_DIALOGUE, 100.0 * d_tot / TOTAL_DIALOGUE))
    print("battle  : %d of %d read by a human (%.2f%%)"
          % (c_tot, TOTAL_CAPTIONS, 100.0 * c_tot / TOTAL_CAPTIONS))
    print()
    print("Machine passes are NOT counted here. rec55 was read end to end three")
    print("times by Claude and appears nowhere above - that is deliberate, this")
    print("number is only about human eyes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
