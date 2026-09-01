# -*- coding: utf-8 -*-
"""Give the caption sheets a live byte counter and the budget to compare it to.

A proofreader cannot see either number. Captions are drawn by the menu reader,
so bytes 0x2E-0x3D - '.' '/' 0-9 ':' ';' '<' '=' - are emitted as TWO-byte
private glyphs; every other character is one. So "Might sting a bit?" is 19
bytes but "3.5 sec" is 11, and a line that looks shorter can be bigger. And the
space a rewrite may occupy is whatever the field already holds, which is
invisible from the sheet entirely.

Three columns:

    J  budget   how many bytes this field holds        (static)
    K  bytes    what the proposal in D currently costs (formula, live)
    L  fits     OK, or "over by N"                     (formula, live)

K and L are FORMULAS, so they update as the proofreader types - the point is
to answer "will this fit" before anyone runs a tool, not after.

THE BUDGET. srvc_apply pads a caption with trailing spaces, and that run is
spendable because the field START must not move (voice-sync offsets are
absolute). So a field is <text><trailing spaces> and its extent is the budget.
Harvested by scanning the caption regions once and taking, for each distinct
line, the SMALLEST extent seen: the same shout is stored once per unit that can
speak it, the copies are padded differently, and a rewrite has to fit them all.
Validated against the 37 budgets measured the slow way by apply_caption_fixes:
37 of 37 match. Resolvable for 19,075 of 19,213 rows; the rest are left blank
rather than guessed.

Usage: sheets_budget_captions.py <service-account.json> <iso> [--dry-run]
"""
import collections
import hashlib
import io
import json
import os
import re
import sys
import time

import gspread
from google.oauth2.service_account import Credentials

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import encode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "caption_pairs.json")
FIXES = os.path.join(ROOT, "analysis", "caption_fixes.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
# SRVC, and the second copy in the DMY padding that the srvc toolchain never
# touched - both hold the same captions and both are padded, so both count.
REGIONS = [(1313214, 1618), (1826000, 2000)]
NEED_COLS = 12                       # through L
HDR = {"J": "budget", "K": "bytes", "L": "fits"}
# every character the menu encoder spends 2 bytes on
WIDE = "[./0-9:;<=]"
F_BYTES = ('=IF($D%(r)d="","",LEN($D%(r)d)+LEN($D%(r)d)'
           '-LEN(REGEXREPLACE($D%(r)d,"' + WIDE + '","")))')
F_FITS = ('=IF($K%(r)d="","",IF($J%(r)d="","?",'
          'IF($K%(r)d<=$J%(r)d,"OK","over by "&($K%(r)d-$J%(r)d))))')


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


def extents(iso):
    """Smallest field extent for each distinct caption body."""
    ext = {}
    f = open(iso, "rb")
    for lba, n in REGIONS:
        f.seek(lba * 2048)
        blob = f.read(n * 2048)
        for m in re.finditer(rb"[^\x00]+", blob):
            raw = m.group(0)
            body = raw.rstrip(b" ")
            if not body or not body.startswith(b'"'):
                continue
            if body not in ext or len(raw) < ext[body]:
                ext[body] = len(raw)
    f.close()
    return ext


def budgets(iso):
    ext = extents(iso)
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]
    # A row that has already been rewritten no longer holds the english
    # caption_pairs.json records, so looking it up by that text finds
    # nothing and the budget comes back blank on exactly the rows a
    # proofreader just worked on. Consult what was actually applied
    # first - the image is the authority on the current text.
    applied = {}
    if os.path.exists(FIXES):
        for x in json.load(io.open(FIXES, encoding="utf-8")):
            applied[x["key"]] = x["text"]
    out = {}
    for p in pairs:
        h = hashlib.sha1(p["jp"].encode("cp932", "ignore")).hexdigest()[:12]
        k = "b%d:%s" % (p["b"], h)
        b = None
        if k in applied:
            b = ext.get(encode(applied[k], "menuhw"))
        if not b:
            b = ext.get(encode(p["en"], "menuhw"))
        if b:
            out[k] = b
    print("%d caption field(s) harvested, budget known for %d of %d rows"
          % (len(ext), len(out), len(pairs)))
    return out


def main():
    key_file, iso = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    bud = budgets(iso)

    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        if not f["name"].startswith("SRWZ proofread "):
            continue
        sh = retry(gc.open_by_key, f["id"])
        ws = dict((w.title, w) for w in retry(sh.worksheets))
        titles = sorted(t for t in ws if t.startswith("blk"))
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
        body, known, rows = [], 0, 0
        for title, rng in zip(titles, got):
            keys = [(r[0] if r else "") for r in (rng.get("values") or [])]
            if len(keys) < 2:
                continue
            col = [[HDR["J"], HDR["K"], HDR["L"]]]
            for i, k in enumerate(keys[1:], start=2):
                b = bud.get(k.strip(), "")
                if b:
                    known += 1
                rows += 1
                col.append([b, F_BYTES % {"r": i}, F_FITS % {"r": i}])
            body.append({"range": "%s!J1" % title, "values": col})
        print("%-44s %d row(s), budget on %d" % (f["name"], rows, known))
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
