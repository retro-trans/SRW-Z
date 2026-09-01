# -*- coding: utf-8 -*-
"""Back up every proofreader entry from the sheets, keyed by row key.

WHY THIS MUST RUN BEFORE ANY RE-PUSH. sheets_push.py writes each sheet as a
whole rectangle and puts "" in the four proofreader columns:

    vals = [key, speaker, jp, en, "", "", "", "", free, cols, lines]
                                   ^^  ^^  ^^  ^^
                            PROPOSED ENGLISH / status / note / by

So pushing over a sheet a proofreader has worked in DESTROYS that work. The
re-ordering pass on 2026-08-31 needed exactly such a push, which is what this
is for: dump the four columns first, restore them on the way back in.

The dump is keyed by the row key, never by position - the whole point of the
re-ordering is that positions move. Keys do not: they are
rec:sha1(japanese):occurrence, and export_proofread.py deliberately numbers the
occurrence in OFFSET order so re-ordering the display cannot renumber them.

Read-only. It never writes to a sheet.

Usage: sheets_preserve.py <service-account.json> [--out FILE]
"""
import io
import json
import os
import sys
import time

import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
NL = chr(10)
# THE TWO SHEET SHAPES ARE NOT THE SAME and reading one with the other's
# column map silently produces a garbage backup. Dialogue sheets carry a
# speaker column that caption sheets do not, so everything after it shifts:
#
#   rec### (dialogue) A key  B speaker  C jp  D en  E PROP  F status  G note  H by
#   blk### (captions) A key  B jp       C en  D PROP  E status  F note  G by  H cols
#
# Read with the dialogue map, every caption row looks filled in because H holds
# the column count - 19,211 phantom "entries" on the first run of this.
C_KEY = 0
COLMAP = {"rec": (4, 5, 6, 7), "blk": (3, 4, 5, 6)}


def retry(fn, *a, **k):
    """Retry rate limits AND transient 5xx.

    Sheets returns a bare 503 "service is currently unavailable" often enough
    that treating it as fatal loses a whole backup run partway through. Both
    classes are transient and safe to retry - every call here is a READ.
    """
    for attempt in range(8):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            msg = str(e)
            transient = ("429" in msg or "RESOURCE_EXHAUSTED" in msg
                         or "500" in msg or "502" in msg or "503" in msg)
            if not transient:
                raise
            wait = 5 * (attempt + 1)
            print("   %s - retrying in %ds"
                  % ("rate limited" if "429" in msg else "service unavailable",
                     wait))
            time.sleep(wait)
    raise SystemExit("gave up after repeated transient errors")


def main():
    key_file = sys.argv[1]
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(ROOT, "analysis", "sheet_entries.json"))
    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))

    kept, books, blank = {}, 0, 0
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        if "proofread" not in f["name"]:
            continue
        books += 1
        sh = retry(gc.open_by_key, f["id"])
        titles = [w.title for w in retry(sh.worksheets)
                  if w.title.startswith("rec") or w.title.startswith("blk")]
        # one read for the whole workbook - 172 sheets against a 60/min cap
        # is an instant 429
        got = retry(sh.values_batch_get, ["%s!A2:H" % t for t in titles],
                    params={"majorDimension": "ROWS"})
        n = 0
        for title, rng in zip(titles, got.get("valueRanges", [])):
            cmap = COLMAP[title[:3]]
            for row in rng.get("values", []):
                if not row or not row[C_KEY].strip():
                    continue
                cells = [(row[i].strip() if len(row) > i else "")
                         for i in cmap]
                if not any(cells):
                    blank += 1
                    continue
                kept[row[C_KEY].strip()] = cells
                n += 1
        print("%-44s %4d entr%s" % (f["name"][:44], n, "y" if n == 1 else "ies"))
    io.open(out, "w", encoding="utf-8", newline=NL).write(
        json.dumps(kept, ensure_ascii=False, indent=1))
    print()
    print("%d workbook(s), %d rows with proofreader input, %d untouched rows"
          % (books, len(kept), blank))
    print("wrote %s" % out)
    if not kept:
        print("NOTHING TO PRESERVE - no proofreader has filled a cell yet, so a "
              "re-push cannot destroy work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
