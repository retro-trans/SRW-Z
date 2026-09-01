# -*- coding: utf-8 -*-
"""Fill the proofreading workbooks in Google Sheets from dialogue.json.

One worksheet per STAGE record, rows in script order. The proofreader reads
japanese beside our english and writes a replacement only where he thinks one
is needed - most cells stay empty, which is what keeps the import safe: only
non-empty PROPOSED cells are ever considered.

BUDGETS ARE COLUMNS, NOT FOLKLORE. Each row carries the bytes it has spare,
its widest line in columns and its line count. The box is 3 lines of 34
columns - measured, not assumed: all 68,114 shipped rows fit inside it and the
distribution stops dead at 34. Bytes are the scarce resource, not columns:
the median row has 12 spare and 6,702 rows have none at all, so those can only
be replaced by something the same length or shorter.

RATE LIMITS. The Sheets API allows 60 write requests per minute per user, and
a workbook here needs one sheet per record. Everything is therefore batched -
all sheets in a workbook created in a single batch_update, all values written
in a single values_batch_update - and 429s back off and retry rather than
failing the run half-populated.

RE-PUSHING OVER LIVE WORK. This writes each sheet as a whole rectangle, so a
plain re-push blanks the four proofreader columns. Pass --preserve with the
file sheets_preserve.py produced and those cells are written back by KEY, which
is what makes re-ordering the rows safe: positions move, keys do not. Always
run sheets_preserve.py IMMEDIATELY before the push - anything a proofreader
types between the backup and the push is outside the file and will be lost.

Usage: sheets_push.py <service-account.json> [--only N] [--preserve FILE]
                      [--dry-run]
"""
import io
import json
import os
import sys
import time

import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "proofread")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
HDR = ["key", "speaker", "japanese", "current english", "PROPOSED ENGLISH",
       "status", "note", "by", "free bytes", "cols", "lines"]
# widths in pixels, by column index
WIDTHS = [130, 90, 300, 300, 300, 90, 200, 70, 80, 55, 55]


def retry(fn, *a, **k):
    """Sheets returns 429 under sustained writes; back off rather than die."""
    for attempt in range(6):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            wait = 5 * (attempt + 1)
            print("      rate limited, waiting %ds" % wait)
            time.sleep(wait)
    raise SystemExit("gave up after repeated rate limits")


def main():
    key = sys.argv[1]
    dry = "--dry-run" in sys.argv
    only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
    data = json.load(io.open(os.path.join(SRC, "dialogue.json"), encoding="utf-8"))
    groups = json.load(io.open(os.path.join(SRC, "grouping.json"), encoding="utf-8"))
    keep = {}
    if "--preserve" in sys.argv:
        pf = sys.argv[sys.argv.index("--preserve") + 1]
        keep = json.load(io.open(pf, encoding="utf-8"))
        print("preserving %d proofreader entr%s from %s"
              % (len(keep), "y" if len(keep) == 1 else "ies", os.path.basename(pf)))
    else:
        print("WARNING: no --preserve file. Any proofreader entry in these "
              "sheets will be BLANKED.")

    gc = gspread.authorize(Credentials.from_service_account_file(key, scopes=SCOPES))
    books = {f["name"]: f["id"] for f in gc.list_spreadsheet_files()}

    for gi, recs in enumerate(groups, 1):
        name = [n for n in books if n.startswith("SRWZ proofread %d " % gi)]
        if not name:
            print("workbook %d: NOT FOUND - skipping" % gi)
            continue
        if only and gi != only:
            continue
        sh = retry(gc.open_by_key, books[name[0]])
        print("%s  (%d records)" % (name[0], len(recs)))
        have = {w.title: w for w in sh.worksheets()}
        # create every missing sheet in ONE batch_update
        want = ["rec%03d" % r for r in recs]
        missing = [t for t in want if t not in have]
        if missing and not dry:
            reqs = [{"addSheet": {"properties": {
                        "title": t,
                        "gridProperties": {"rowCount": len(data[str(int(t[3:]))]) + 5,
                                           "columnCount": len(HDR),
                                           "frozenRowCount": 1}}}}
                    for t in missing]
            retry(sh.batch_update, {"requests": reqs})
            have = {w.title: w for w in sh.worksheets()}
            print("   created %d sheets" % len(missing))
        if dry:
            print("   would write %d sheets, %d rows"
                  % (len(want), sum(len(data[str(r)]) for r in recs)))
            continue
        # all values for the workbook in ONE values_batch_update
        body = []
        for r in recs:
            rows = data[str(r)]
            vals = [HDR]
            for x in rows:
                # restored by KEY, never by position - the rows have moved
                p, st, nt, by = keep.get(x["key"], ("", "", "", ""))
                vals.append([x["key"], x["speaker"], x["jp"], x["en"],
                             p, st, nt, by,
                             x["free"], x["cols"], x["lines"]])
            body.append({"range": "rec%03d!A1" % r, "values": vals})
        retry(sh.values_batch_update,
              {"valueInputOption": "RAW", "data": body})
        print("   wrote %d rows across %d sheets"
              % (sum(len(data[str(r)]) for r in recs), len(recs)))
        # cosmetics: column widths, in one more batch
        reqs = []
        for r in recs:
            sid = have["rec%03d" % r].id
            for ci, w in enumerate(WIDTHS):
                reqs.append({"updateDimensionProperties": {
                    "range": {"sheetId": sid, "dimension": "COLUMNS",
                              "startIndex": ci, "endIndex": ci + 1},
                    "properties": {"pixelSize": w}, "fields": "pixelSize"}})
        for i in range(0, len(reqs), 200):
            retry(sh.batch_update, {"requests": reqs[i:i + 200]})
        # drop the default empty sheet a new spreadsheet is created with, so
        # the workbook contains nothing but record sheets
        for w in sh.worksheets():
            if w.title == "Sheet1" and w.row_count and not w.get_all_values():
                retry(sh.del_worksheet, w)
                print("   removed the empty default Sheet1")
        print("   formatted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
