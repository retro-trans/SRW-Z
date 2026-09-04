# -*- coding: utf-8 -*-
"""Push the prologue/interlude NARRATION (DATA/MTV_PROS.BIN) to a 'narration'
worksheet so it can be proofread like the dialogue.

Source: analysis/narration_sheet.json (built by extract_narration.py) - one row
per rawt chunk, full japanese beside our current english. The proofreader writes
into PROPOSED ENGLISH; only non-empty proposed cells matter on pull-back.

Re-pushing blanks the proofreader columns unless --preserve is given (same
key-based restore as sheets_push). Narration cells are whole paragraphs, so the
japanese/english columns are wide.

Usage: sheets_push_narration.py <service-account.json> [--book N] [--preserve F]
                                [--dry-run]
"""
import io, json, os, sys, time
import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "narration_sheet.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
HDR = ["key", "japanese", "current english", "PROPOSED ENGLISH",
       "status", "note", "by", "lines", "jp bytes"]
WIDTHS = [130, 460, 460, 460, 90, 220, 70, 55, 70]
SHEET = "narration"


def retry(fn, *a, **k):
    for attempt in range(6):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            time.sleep(5 * (attempt + 1))
            print("   rate limited, retrying")
    raise SystemExit("gave up after repeated rate limits")


def main():
    key = sys.argv[1]
    dry = "--dry-run" in sys.argv
    book = int(sys.argv[sys.argv.index("--book") + 1]) if "--book" in sys.argv else 1
    keep = {}
    if "--preserve" in sys.argv:
        keep = json.load(io.open(sys.argv[sys.argv.index("--preserve") + 1],
                                 encoding="utf-8"))
        print("preserving %d proofreader entries" % len(keep))
    else:
        print("WARNING: no --preserve; any proofreader entry on the narration "
              "sheet will be BLANKED.")
    rows = json.load(io.open(SRC, encoding="utf-8"))
    print("%d narration chunks to push" % len(rows))

    gc = gspread.authorize(Credentials.from_service_account_file(key, scopes=SCOPES))
    books = {f["name"]: f["id"] for f in gc.list_spreadsheet_files()}
    name = [n for n in books if n.startswith("SRWZ proofread %d " % book)]
    if not name:
        raise SystemExit("workbook 'SRWZ proofread %d ...' not found (have: %s)"
                         % (book, ", ".join(sorted(books)[:8])))
    sh = retry(gc.open_by_key, books[name[0]])
    print("target workbook: %s" % name[0])

    have = {w.title: w for w in sh.worksheets()}
    if SHEET not in have:
        if dry:
            print("   would create sheet '%s'" % SHEET)
        else:
            retry(sh.add_worksheet, title=SHEET, rows=len(rows) + 5,
                  cols=len(HDR))
            print("   created sheet '%s'" % SHEET)
    ws = None if dry else sh.worksheet(SHEET)

    vals = [HDR]
    for x in rows:
        p, st, nt, by = keep.get(x["key"], ("", "", "", ""))
        vals.append([x["key"], x["jp"], x["en"], p, st, nt, by,
                     x["lines"], x["jp_bytes"]])
    if dry:
        print("   would write %d rows x %d cols" % (len(vals), len(HDR)))
        return
    retry(ws.update, "A1", vals, value_input_option="RAW")
    # widen columns + freeze header
    reqs = [{"updateDimensionProperties": {
                "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": w}, "fields": "pixelSize"}}
            for i, w in enumerate(WIDTHS)]
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": ws.id,
                       "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"}})
    retry(sh.batch_update, {"requests": reqs})
    print("   wrote %d narration rows to '%s'" % (len(rows), SHEET))


if __name__ == "__main__":
    main()
