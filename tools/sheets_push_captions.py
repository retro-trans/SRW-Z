# -*- coding: utf-8 -*-
"""Fill the battle-line proofreading workbooks (7 and 8) from caption_pairs.

One worksheet per SRVC block. A block is one character's voice - block 60 is a
young male speaking in 僕, block 61 a villain going フハハハ - so a block sheet
is a character sheet, which is the only way caption drift shows up. No single
line looks wrong on its own; they only disagree with each other. ビーター殺法
had four different english names before anyone read one character end to end.

Two things differ from the dialogue workbooks:

  NO BYTE BUDGET. srvc_apply --free repoints the sequence records, so a caption
  may be any length. There is no slot to overflow, so no "free bytes" column.

  WIDTH IS THE ONLY LIMIT, and it is soft. 83% of shipped captions are 38
  columns or less and the box truncates beyond roughly that, so 38 is shown as
  a guide rather than enforced - 3,300 shipped lines are already wider and the
  import does not refuse them.

Lines are DEDUPLICATED by japanese+english: the same shout is stored once per
unit that can speak it, and proofreading it nine times is wasted effort.

Usage: sheets_push_captions.py <service-account.json> [--dry-run]
"""
import collections
import hashlib
import io
import json
import os
import sys
import time
import unicodedata

import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "caption_pairs.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
NL = chr(10)
HDR = ["key", "japanese", "current english", "PROPOSED ENGLISH",
       "status", "note", "by", "cols"]
WIDTHS = [150, 320, 330, 330, 90, 200, 70, 55]
GUIDE = 38


def cols(s):
    return max(sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                   for c in line) for line in s.split(NL))


def retry(fn, *a, **k):
    for attempt in range(6):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            wait = 10 * (attempt + 1)
            print("      rate limited, waiting %ds" % wait)
            time.sleep(wait)
    raise SystemExit("gave up after repeated rate limits")


def main():
    key = sys.argv[1]
    dry = "--dry-run" in sys.argv
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]

    by = collections.defaultdict(list)
    for p in pairs:
        h = hashlib.sha1(p["jp"].encode("cp932", "ignore")).hexdigest()[:12]
        by[p["b"]].append({"key": "b%d:%s" % (p["b"], h),
                           "jp": p["jp"], "en": p["en"],
                           "cols": cols(p["en"])})
    blocks = sorted(by)
    half = len(blocks) // 2
    split = [blocks[:half], blocks[half:]]
    print("%d blocks, %d lines -> workbooks 7 and 8"
          % (len(blocks), sum(len(v) for v in by.values())))

    gc = gspread.authorize(Credentials.from_service_account_file(key,
                                                                 scopes=SCOPES))
    books = {f["name"]: f["id"] for f in gc.list_spreadsheet_files()}
    for n, group in zip((7, 8), split):
        name = [x for x in books if x.startswith("SRWZ proofread %d " % n)]
        if not name:
            print("workbook %d not found - skipping" % n)
            continue
        rows = sum(len(by[b]) for b in group)
        print("%s  (%d blocks, %d lines)" % (name[0], len(group), rows))
        if dry:
            continue
        sh = retry(gc.open_by_key, books[name[0]])
        have = {w.title: w for w in retry(sh.worksheets)}
        want = ["blk%03d" % b for b in group]
        missing = [t for t in want if t not in have]
        if missing:
            reqs = [{"addSheet": {"properties": {
                        "title": t,
                        "gridProperties": {
                            "rowCount": len(by[int(t[3:])]) + 5,
                            "columnCount": len(HDR),
                            "frozenRowCount": 1}}}} for t in missing]
            for i in range(0, len(reqs), 100):
                retry(sh.batch_update, {"requests": reqs[i:i + 100]})
            have = {w.title: w for w in retry(sh.worksheets)}
            print("   created %d sheets" % len(missing))
        body = []
        for b in group:
            vals = [HDR] + [[r["key"], r["jp"], r["en"], "", "", "", "",
                             r["cols"]] for r in by[b]]
            body.append({"range": "blk%03d!A1" % b, "values": vals})
        for i in range(0, len(body), 60):
            retry(sh.values_batch_update,
                  {"valueInputOption": "RAW", "data": body[i:i + 60]})
        print("   wrote %d lines" % rows)
        reqs = []
        for b in group:
            sid = have["blk%03d" % b].id
            for ci, w in enumerate(WIDTHS):
                reqs.append({"updateDimensionProperties": {
                    "range": {"sheetId": sid, "dimension": "COLUMNS",
                              "startIndex": ci, "endIndex": ci + 1},
                    "properties": {"pixelSize": w}, "fields": "pixelSize"}})
        for i in range(0, len(reqs), 200):
            retry(sh.batch_update, {"requests": reqs[i:i + 200]})
        for w in retry(sh.worksheets):
            if w.title == "Sheet1":
                try:
                    retry(sh.del_worksheet, w)
                except Exception:
                    pass
        print("   formatted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
