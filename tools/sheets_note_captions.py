# -*- coding: utf-8 -*-
"""Write a feedback column back to the battle-line workbooks.

A proofreader cannot see the byte budget. Captions are drawn by the menu
reader, so '.' and 0-9 cost TWO bytes each, and the space a line may occupy is
whatever the japanese it replaced took - which is invisible from the sheet. So
37 of 83 rewrites could not be applied, and without this column the only signal
would be that some lines changed in game and some did not.

Column I says what happened to each proposal:

    applied                      it is in the build
    OVER BUDGET by N bytes ...   it is not, and by how much it missed
    already matches the build    the proposal equals the current line

Only column I is written. The proofreader's own columns are never touched -
this tool cannot overwrite their work even if it is wrong about a row.

Usage: sheets_note_captions.py <service-account.json> [--dry-run]
"""
import io
import json
import os
import sys
import time

import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXES = os.path.join(ROOT, "analysis", "caption_fixes.json")
OVER = os.path.join(ROOT, "analysis", "caption_over_budget.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
NL = chr(10)
HDR = "claude"
COL = "I"          # A..H are the existing columns
C_KEY = 0


def retry(fn, *a, **kw):
    for attempt in range(6):
        try:
            return fn(*a, **kw)
        except gspread.exceptions.APIError as e:
            code = getattr(e.response, "status_code", 0)
            if code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(10 * (attempt + 1))
    raise SystemExit("gave up after repeated rate limits")


def notes():
    fixes = json.load(io.open(FIXES, encoding="utf-8"))
    over = dict((d["key"], d)
                for d in json.load(io.open(OVER, encoding="utf-8")))
    out = {}
    for x in fixes:
        k = x["key"]
        if k in over:
            d = over[k]
            out[k] = ("OVER BUDGET by %d bytes - the field holds %d, this "
                      "needs %d. Shorten by %d and it goes in. NOTE: '.' and "
                      "0-9 cost 2 bytes each here."
                      % (d["over"], d["budget"], d["needs"], d["over"]))
        elif x["text"] == x["was"]:
            out[k] = "already matches the build - no change needed"
        else:
            out[k] = "applied"
    return out


def main():
    key_file = sys.argv[1]
    dry = "--dry-run" in sys.argv
    note = notes()
    print("%d row(s) to annotate (%d over budget)"
          % (len(note), sum(1 for v in note.values() if v.startswith("OVER"))))

    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        if not f["name"].startswith("SRWZ proofread "):
            continue
        sh = retry(gc.open_by_key, f["id"])
        titles = [w.title for w in retry(sh.worksheets)
                  if w.title.startswith("blk")]
        if not titles:
            continue
        # The sheets were created exactly 8 columns wide, so writing I1
        # fails with "exceeds grid limits" until the grid is widened.
        # Widen first, and only the sheets that actually need it.
        props = dict((w.title, w) for w in retry(sh.worksheets))
        grow = [props[t] for t in titles
                if props[t].col_count < 9]
        if grow and not dry:
            reqs = [{"appendDimension": {"sheetId": w.id,
                                         "dimension": "COLUMNS",
                                         "length": 9 - w.col_count}}
                    for w in grow]
            for i in range(0, len(reqs), 100):
                retry(sh.batch_update, {"requests": reqs[i:i + 100]})
            print("   widened %d sheet(s) to 9 columns" % len(grow))
        got = retry(sh.values_batch_get,
                    ["%s!A1:A" % t for t in titles])["valueRanges"]
        body, n = [], 0
        for title, rng in zip(titles, got):
            keys = [(r[C_KEY] if r else "") for r in (rng.get("values") or [])]
            if not keys:
                continue
            col = [[HDR]]
            for k in keys[1:]:
                v = note.get(k.strip(), "")
                col.append([v])
                if v:
                    n += 1
            body.append({"range": "%s!%s1" % (title, COL), "values": col})
        print("%-44s %3d annotated row(s) in %d sheet(s)"
              % (f["name"], n, len(titles)))
        if dry:
            continue
        for i in range(0, len(body), 60):
            retry(sh.values_batch_update,
                  {"valueInputOption": "RAW", "data": body[i:i + 60]})
    if dry:
        print("(dry run - nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
