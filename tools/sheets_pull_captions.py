# -*- coding: utf-8 -*-
"""Read the BATTLE-LINE workbooks back. The dialogue puller cannot see them.

WHY THIS EXISTS. sheets_pull.py collects a workbook's sheets with

    titles = [w.title for w in sh.worksheets() if w.title.startswith("rec")]

and the battle workbooks name their sheets blk000, blk004, blk060 - one per
SRVC block, which is one character's voice. So workbooks 7 and 8 were skipped
in SILENCE, with no warning and no zero-row line in the output, and 76
proofread rewrites sat in them unread. Found only by counting sheet entries
against what the puller returned.

CAPTIONS ARE NOT DIALOGUE, in three ways that matter here:

  key       b<block>:<sha1(japanese)[:12]>, minted by sheets_push_captions.py
            from caption_pairs.json - not rec:sha1:occurrence
  encoding  captions are drawn by the MENU reader (0x13A290), so they go
            through patch.encode(mode="menuhw"): every . and 0-9 becomes a
            TWO-byte private glyph. A caption's byte cost is therefore not its
            character count, and a line that looks short can be over budget.
  width     38 columns is a guide, not a limit - 3,300 shipped lines are
            already wider - so a wide line is reported and kept, not dropped.

WHAT IS CHECKED. A proposal is dropped, never repaired, if it cannot be
encoded at all or if its key does not resolve; a line quietly altered to fit
is no longer the line the proofreader approved. Everything else is reported
and kept.

Read-only. Writes analysis/caption_fixes.json for the applier.

Usage: sheets_pull_captions.py <service-account.json> [--out FILE]
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "caption_pairs.json")
OUT = os.path.join(ROOT, "analysis", "caption_fixes.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
NL = chr(10)
GUIDE = 38
# sheets_push_captions.HDR
C_KEY, C_JP, C_CUR, C_NEW, C_STATUS, C_NOTE, C_BY = range(7)


def cols(s):
    return max(sum(2 if unicodedata.east_asian_width(c) in "WF" else 1
                   for c in line) for line in s.split(NL))


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


def index():
    """key -> (block, japanese, current english). Same minting as the push."""
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]
    idx = {}
    for p in pairs:
        h = hashlib.sha1(p["jp"].encode("cp932", "ignore")).hexdigest()[:12]
        idx["b%d:%s" % (p["b"], h)] = (p["b"], p["jp"], p["en"])
    return idx


def main():
    key_file = sys.argv[1]
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else OUT)
    idx = index()
    print("%d caption rows indexed" % len(idx))

    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))
    fixes, bad, wide = [], [], 0
    by_who = collections.Counter()
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        name = f["name"]
        if not name.startswith("SRWZ proofread "):
            continue
        sh = retry(gc.open_by_key, f["id"])
        titles = [w.title for w in retry(sh.worksheets)
                  if w.title.startswith("blk")]
        if not titles:
            continue
        # one batched read per workbook: a read per sheet is an instant 429
        got = retry(sh.values_batch_get,
                    ["%s!A1:H" % t for t in titles])["valueRanges"]
        n = 0
        for rng in got:
            for row in (rng.get("values") or [])[1:]:
                if len(row) <= C_NEW:
                    continue
                proposed = (row[C_NEW] or "").strip()
                if not proposed:
                    continue
                n += 1
                k = (row[C_KEY] or "").strip()
                who = (row[C_BY] or "").strip() if len(row) > C_BY else ""
                who = who or "unattributed"
                if k not in idx:
                    bad.append((k, proposed, "key not in caption_pairs"))
                    continue
                blk, jp, cur = idx[k]
                if proposed == cur:
                    continue
                try:
                    enc = encode(proposed, "menuhw")
                except (UnicodeEncodeError, ValueError) as e:
                    bad.append((k, proposed, "not encodable: %s" % e))
                    continue
                w = cols(proposed)
                if w > GUIDE:
                    wide += 1
                by_who[who] += 1
                fixes.append({"key": k, "b": blk, "jp": jp, "was": cur,
                              "text": proposed, "by": who,
                              "cols": w, "bytes": len(enc),
                              "was_bytes": len(encode(cur, "menuhw"))})
        print("%-44s %3d proposal(s) in %d sheet(s)" % (name, n, len(titles)))

    print("\n%d usable rewrite(s), %d rejected, %d wider than the %d-column "
          "guide" % (len(fixes), len(bad), wide, GUIDE))
    for n, v in by_who.most_common():
        print("   %-16s %d" % (n, v))
    for k, t, why in bad[:15]:
        print("   DROPPED %-22s %s" % (k, why))
        print("      %r" % t[:70])
    grow = [x for x in fixes if x["bytes"] > x["was_bytes"]]
    print("\n%d rewrite(s) are LONGER than what they replace "
          "(%d bytes at most) - the applier decides if they fit"
          % (len(grow), max([x["bytes"] - x["was_bytes"] for x in grow] or [0])))
    io.open(out, "w", encoding="utf-8", newline=NL).write(
        json.dumps(fixes, ensure_ascii=False, indent=1))
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
