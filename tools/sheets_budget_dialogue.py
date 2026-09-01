# -*- coding: utf-8 -*-
"""Live budget, width and line count for the DIALOGUE sheets.

The caption sheets got this in sheets_budget_captions.py. Dialogue needs the
same thing but not the same arithmetic, and the differences are the whole
point:

  ENCODING   captions go through the menu reader, where '.' and 0-9 cost TWO
             bytes. Dialogue does NOT - 43,722 of the 68,114 shipped rows
             contain a byte in 0x2E-0x3D, starting with the full stop. Here a
             byte is one per ASCII character and two per fullwidth one, and
             that is also the column width, so bytes and columns agree per
             line.

  SLOT       a dialogue row has a fixed slot and 6,702 rows have ZERO spare
             bytes. The sheet already carries "free bytes" for the CURRENT
             line, so the budget for a REWRITE is that plus what the current
             line spends - which is slot - 1, the same bound sheets_pull.py
             enforces.

  SHAPE      3 body lines of 34 columns. The proposed cell holds the whole
             row, speaker line included, so the body is everything after the
             first newline.

Four live columns and one derived bound:

    L  budget   slot - 1, from column D and the existing "free bytes"
    M  bytes    what the proposal in E costs
    N  widest   its widest BODY line, in columns
    O  lines    its body line count
    P  fits     OK, or the first rule it breaks

P also flags the crash signature verify_boxes exists to catch: a 3-line row
wider than 30 columns. That is not over budget and not over 34 - it renders,
and then the game dies on that row - so it has to be called out separately or
it looks fine right up until it is shipped.

Everything is a FORMULA, so it answers "will this fit" while the line is being
written rather than after a tool rejects it.

Usage: sheets_budget_dialogue.py <service-account.json> [--dry-run] [--only SHEET]
"""
import sys
import time

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
NEED_COLS = 16                      # through P
MAXLINES, WIDTH, RISK = 3, 34, 30
HDR = ["budget", "bytes", "widest", "lines", "fits"]

# BYTES and COLUMNS are not the same measure here, and conflating them is
# wrong in both directions. In cp932 every non-ASCII character is 2 bytes, but
# WIDTH follows east_asian_width, where the "ambiguous" class - U+2026 ...,
# U+2019 ', U+266A - is 2 bytes and only ONE column. The project's own cols()
# counts W and F only, so the sheet has to agree with it or it will predict a
# refusal that never comes.
B = 'LEN(%(c)s)+LEN(REGEXREPLACE(%(c)s,"[[:ascii:]]",""))'
# everything that is NOT wide/fullwidth, stripped, leaves the 2-column chars
NOT_WF = (u"[^　-〿぀-ヿ一-鿿"
          u"！-｠￠-￦]")
C = 'LEN(%(c)s)+LEN(REGEXREPLACE(%(c)s,"' + NOT_WF + '",""))'
BODY = 'MID($E%(r)d,FIND(CHAR(10),$E%(r)d)+1,LEN($E%(r)d))'
PARTS = 'SPLIT(%s,CHAR(10),TRUE,FALSE)' % BODY

F_BUDGET = ('=IF($D%(r)d="","",' + (B % {"c": "$D%(r)d"}) + '+N($I%(r)d))')
F_BYTES = '=IF($E%(r)d="","",' + (B % {"c": "$E%(r)d"}) + ')'
F_WIDEST = ('=IF($E%(r)d="","",IFERROR(MAX(ARRAYFORMULA(' +
            (C % {"c": PARTS}) + ')),' + (C % {"c": "$E%(r)d"}) + '))')
F_LINES = ('=IF($E%(r)d="","",LEN($E%(r)d)-LEN(SUBSTITUTE($E%(r)d,CHAR(10),"")))')
F_FITS = ('=IF($M%(r)d="","",'
          'IF($O%(r)d>' + str(MAXLINES) + ',"TOO MANY LINES ("&$O%(r)d&")",'
          'IF($N%(r)d>' + str(WIDTH) + ',"TOO WIDE ("&$N%(r)d&" cols)",'
          'IF(AND($O%(r)d=' + str(MAXLINES) + ',$N%(r)d>' + str(RISK) + '),'
          '"3 lines >' + str(RISK) + ' cols - re-wrap, crash risk",'
          'IF($L%(r)d="","?",'
          'IF($M%(r)d<=$L%(r)d,"OK","over by "&($M%(r)d-$L%(r)d)&" bytes"))))))')


def retry(fn, *a, **kw):
    for attempt in range(6):
        try:
            return fn(*a, **kw)
        except gspread.exceptions.APIError as e:
            if getattr(e.response, "status_code", 0) not in (429, 500, 502,
                                                             503, 504):
                raise
            time.sleep(10 * (attempt + 1))
    raise SystemExit("gave up after repeated rate limits")


def main():
    key_file = sys.argv[1]
    dry = "--dry-run" in sys.argv
    only = (sys.argv[sys.argv.index("--only") + 1]
            if "--only" in sys.argv else None)

    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        if not f["name"].startswith("SRWZ proofread "):
            continue
        sh = retry(gc.open_by_key, f["id"])
        ws = dict((w.title, w) for w in retry(sh.worksheets))
        titles = sorted(t for t in ws if t.startswith("rec"))
        if only:
            titles = [t for t in titles if t == only]
        if not titles:
            continue
        grow = [ws[t] for t in titles if ws[t].col_count < NEED_COLS]
        if grow and not dry:
            reqs = [{"appendDimension": {"sheetId": w.id,
                                         "dimension": "COLUMNS",
                                         "length": NEED_COLS - w.col_count}}
                    for w in grow]
            for i in range(0, len(reqs), 100):
                retry(sh.batch_update, {"requests": reqs[i:i + 100]})
            print("   widened %d sheet(s) to %d columns" % (len(grow),
                                                            NEED_COLS))
        got = retry(sh.values_batch_get,
                    ["%s!A1:A" % t for t in titles])["valueRanges"]
        body, rows = [], 0
        for title, rng in zip(titles, got):
            keys = [(r[0] if r else "") for r in (rng.get("values") or [])]
            if len(keys) < 2:
                continue
            col = [list(HDR)]
            for i in range(2, len(keys) + 1):
                d = {"r": i}
                col.append([F_BUDGET % d, F_BYTES % d, F_WIDEST % d,
                            F_LINES % d, F_FITS % d])
                rows += 1
            body.append({"range": "%s!L1" % title, "values": col})
        print("%-44s %d row(s) in %d sheet(s)" % (f["name"], rows, len(titles)))
        if dry:
            continue
        for i in range(0, len(body), 40):
            retry(sh.values_batch_update,
                  {"valueInputOption": "USER_ENTERED", "data": body[i:i + 40]})
    if dry:
        print("(dry run - nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
