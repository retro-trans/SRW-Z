# -*- coding: utf-8 -*-
"""Cut the exported review files into agent-sized slices.

Only DIALOGUE rows go out for proofreading: rows whose Japanese has a speaker
line and a body. Short label rows (unit and faction names like アクシズ/Axis)
are skipped - they are not prose and were not what DeepSeek got wrong.

Each slice is a self-contained JSON list; the agent writes its corrections to
analysis/review/fixes/<slice>.json so nothing large passes through chat.

Usage: make_slices.py <rows-per-slice> <rec> [<rec> ...]
"""
import glob
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(WORK, "analysis", "review")
SLI = os.path.join(REV, "slices")


def main():
    per = int(sys.argv[1])
    recs = [int(a) for a in sys.argv[2:]]
    if not os.path.isdir(SLI):
        os.makedirs(SLI)
    total = 0
    for n in recs:
        d = json.load(io.open(os.path.join(REV, "rec%03d.json" % n), encoding="utf-8"))
        # Spoken dialogue only. A row with no kagi quote is a glossary popup
        # description: menu-drawn, where fullwidth punctuation is CORRECT, so
        # agents must not be invited to "fix" it to ASCII.
        prose = [r for r in d if chr(10) in r["jp"] and len(r["jp"]) > 10
                 and chr(0x300C) in r["en"]]
        for i in range(0, len(prose), per):
            chunk = prose[i:i + per]
            name = "rec%03d_%03d.json" % (n, i // per)
            json.dump(chunk, io.open(os.path.join(SLI, name), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=0)
            total += 1
        print("rec %-4d %4d prose rows -> %d slices" % (n, len(prose), (len(prose) + per - 1) // per))
    print("\n%d slices in %s" % (total, SLI))


if __name__ == "__main__":
    main()
