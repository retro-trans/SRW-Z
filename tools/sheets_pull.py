# -*- coding: utf-8 -*-
"""Read the proofreader's work back, validate every line, emit row_fixes.json.

Only NON-EMPTY 'PROPOSED ENGLISH' cells are considered. That is the whole
safety model: the proofreader touches the lines he wants changed and leaves the
rest alone, so a pass over the sheet can never silently rewrite the script.

Nothing reaches the image until it survives every check below. A proposal that
fails is reported with the reason and dropped - never trimmed, rewrapped or
"fixed up" on the proofreader's behalf, because a line quietly altered into
something that fits is no longer the line he approved.

WHAT IS CHECKED, and why each one is here:

  key resolves    the row is found by rec + sha1(japanese) + occurrence, never
                  by offset - offsets move on every rebuild
  byte slot       6,702 rows have ZERO spare bytes; a longer line needs the row
                  relocated, and rec137 proves that is not always possible
  34 columns      the measured ceiling: all 68,114 shipped rows fit 34 and the
                  distribution stops dead there
  3 body lines    a fourth line overflows the box
  cp932           the game has no unicode - a smart quote or an accented letter
                  cannot be encoded at all
  control bytes   0x2E-0x3D are COMMANDS to the menu reader, not characters
  $n and <NN>     macros the engine expands; dropping one changes what prints
  glossary links  a link whose term is not in the keyword bank CRASHES the
                  scene when the line is displayed

Usage: sheets_pull.py <service-account.json> <iso> [--by NAME] [--out FILE]
"""
import hashlib
import io
import json
import os
import re
import struct
import sys
import unicodedata

import gspread
from google.oauth2.service_account import Credentials

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from fix_dead_links import keywords

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
SECTOR, LBA, SIZE, BASE = 2048, 1651029, 3910128, 0x7566F0
NL = chr(10)
KAGI = chr(0x300C)
LINK_OPEN, LINK_CLOSE = chr(0x300A), chr(0x300B)
MAXLINES, WIDTH = 3, 34
MACRO = re.compile(r"\$n|<-?\d+>")
LINK = re.compile(LINK_OPEN + "([^" + LINK_CLOSE + "]*)" + LINK_CLOSE)
C_KEY, C_EN, C_PROP, C_STATUS, C_NOTE, C_BY = 0, 3, 4, 5, 6, 7
# There is more than one proofreader, so who wrote a line cannot be inferred
# from the fact that a cell is filled, and the Sheets API cannot read per-cell
# edit history. The 'by' column is a dropdown for exactly this reason: a
# proposal with no name attached is accepted but reported, never guessed at.
KNOWN = ("Valz", "Hakhan")


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def retry(fn, *a, **k):
    """Sheets caps reads at 60/minute; back off rather than fail half-read."""
    import time
    for attempt in range(6):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            wait = 10 * (attempt + 1)
            print("   rate limited, waiting %ds" % wait)
            time.sleep(wait)
    raise SystemExit("gave up after repeated rate limits")


def index_image(iso):
    """key -> (rec, offset, slot, current text). Same keying as the exporter."""
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    recs = banlz.decompress_all(f.read(SIZE))
    f.close()
    jp = banlz.decompress_all(
        open(os.path.join(ROOT, "extracted", "DATA_STAGE.BIN"), "rb").read())
    idx = {}
    for ri in range(len(recs)):
        if recs[ri][1] is None or jp[ri][1] is None:
            continue
        eb, jb = bytes(recs[ri][1]), bytes(jp[ri][1])
        m = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", eb, p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in m:
                m[ve] = vj
        occ = {}
        for off in sorted(m):
            z = eb.find(b"\x00", off)
            if z <= off:
                continue
            k = z
            while k < len(eb) and eb[k] == 0:
                k += 1
            zj = jb.find(b"\x00", m[off])
            try:
                et = eb[off:z].decode("cp932")
                jt = jb[m[off]:zj].decode("cp932")
            except UnicodeDecodeError:
                continue
            if NL not in et or KAGI not in et:
                continue
            h = hashlib.sha1(jt.encode("cp932", "ignore")).hexdigest()[:12]
            n = occ.get(h, 0)
            occ[h] = n + 1
            idx["%d:%s:%d" % (ri, h, n)] = (ri, off, k - off, et)
    return idx


def check(key, proposed, idx, kw):
    """Return a complaint, or None if the line may be written."""
    if key not in idx:
        return "key not in the image - export may be stale"
    _ri, _off, slot, cur = idx[key]
    if proposed == cur:
        return "identical to the current line"
    try:
        nb = proposed.encode("cp932")
    except UnicodeEncodeError as e:
        return "not encodable as cp932: %s" % e
    # NO 0x2E-0x3D check here. That range is control codes to the MENU reader
    # at 0x13A290, not to the dialogue box: 43,722 of the 68,114 shipped
    # dialogue rows contain one, starting with a full stop. Applying the menu
    # rule here refused 64% of legitimate English.
    if len(nb) >= slot:
        return "needs %d bytes, the row holds %d" % (len(nb) + 1, slot)
    body = proposed.split(NL)[1:]
    if len(body) > MAXLINES:
        return "%d body lines, max %d" % (len(body), MAXLINES)
    w = max([cols(line) for line in body] or [0])
    if w > WIDTH:
        return "%d columns, max %d" % (w, WIDTH)
    if proposed.split(NL)[0] != cur.split(NL)[0]:
        return "speaker changed (%r -> %r); do that as a separate pass" % (
            cur.split(NL)[0], proposed.split(NL)[0])
    was, now = sorted(MACRO.findall(cur)), sorted(MACRO.findall(proposed))
    if was != now:
        return "macros changed: %s -> %s" % (was or "none", now or "none")
    dead = [t for t in LINK.findall(proposed) if t not in kw]
    if dead:
        return "glossary link not in the keyword bank, WOULD CRASH: %s" % dead
    return None


def main():
    key_file, iso = sys.argv[1], sys.argv[2]
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(ROOT, "analysis", "row_fixes.json"))
    # only used when the 'by' dropdown was left blank
    who = sys.argv[sys.argv.index("--by") + 1] if "--by" in sys.argv else "unattributed"

    print("indexing the image...")
    idx = index_image(iso)
    kw = keywords(iso)
    print("   %d rows indexed, %d glossary keywords" % (len(idx), len(kw)))

    gc = gspread.authorize(
        Credentials.from_service_account_file(key_file, scopes=SCOPES))
    fixes, bad, unnamed, seen = [], [], [], 0
    for f in sorted(gc.list_spreadsheet_files(), key=lambda x: x["name"]):
        if "proofread" not in f["name"]:
            continue
        sh = retry(gc.open_by_key, f["id"])
        all_titles = [w.title for w in retry(sh.worksheets)]
        titles = [t for t in all_titles if t.startswith("rec")]
        # NEVER SKIP A WORKBOOK IN SILENCE. This filter once hid 76
        # proofread battle lines for weeks: the battle workbooks name
        # their sheets blk000, blk004 ... one per SRVC block, none of
        # which starts with "rec", so workbooks 7 and 8 produced no rows
        # AND no output at all - indistinguishable from "nobody has
        # touched them". Anything unread is now named out loud.
        skipped = [t for t in all_titles
                   if t not in titles and t != "Sheet1"]
        if skipped:
            print("%s: SKIPPING %d sheet(s) this tool cannot read: %s%s"
                  % (f["name"], len(skipped), ", ".join(skipped[:4]),
                     " ..." if len(skipped) > 4 else ""))
            if all(t.startswith("blk") for t in skipped):
                print("   these are BATTLE CAPTION sheets - "
                      "run sheets_pull_captions.py for them")
        if not titles:
            continue
        # ONE read request per workbook, not one per sheet: 172 sheets against a
        # 60-reads-per-minute cap is an instant 429. Columns A..E only - key and
        # proposal are all that matter, and the japanese is bulky.
        got = retry(sh.values_batch_get,
                    ["%s!A2:H" % t for t in titles],
                    params={"majorDimension": "ROWS"})
        for title, rng in zip(titles, got.get("valueRanges", [])):
            for row in rng.get("values", []):
                if len(row) <= C_PROP:
                    continue
                prop = row[C_PROP].strip()
                if not prop:
                    continue
                seen += 1
                why = check(row[C_KEY], prop, idx, kw)
                where = "%s/%s" % (f["name"][-12:], title)
                if why:
                    bad.append((where, row[C_KEY], why, prop))
                else:
                    ri, off, _slot, cur = idx[row[C_KEY]]
                    by = (row[C_BY].strip() if len(row) > C_BY else "") or who
                    if by not in KNOWN:
                        unnamed.append((where, row[C_KEY], by))
                    note = row[C_NOTE].strip() if len(row) > C_NOTE else ""
                    fixes.append({"rec": ri, "off": "0x%06X" % off, "was": cur,
                                  "text": prop, "by": by,
                                  "why": "proofread by %s%s"
                                         % (by, "; " + note if note else "")})
    print()
    print("proposals found : %d" % seen)
    print("accepted        : %d" % len(fixes))
    print("refused         : %d" % len(bad))
    for where, k, why, prop in bad[:40]:
        print("   %-24s %-22s %s" % (where, k, why))
        print("      %r" % prop.replace(NL, " | ")[:70])
    if unnamed:
        print()
        print("accepted but with no proofreader named (%d):" % len(unnamed))
        for where, k, by in unnamed[:10]:
            print("   %-24s %-22s %r" % (where, k, by))
        print("   ask them to set the 'by' dropdown; credit is guesswork otherwise")
    import collections
    tally = collections.Counter(f["by"] for f in fixes)
    if tally:
        print()
        print("by proofreader: %s" % ", ".join("%s %d" % kv for kv in tally.most_common()))
    io.open(out, "w", encoding="utf-8", newline=NL).write(
        json.dumps(fixes, ensure_ascii=False, indent=1))
    print()
    print("wrote %s - review, then apply with fix_row.py" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
