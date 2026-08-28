# -*- coding: utf-8 -*-
"""Replace individual dialogue rows, from a list of hand-written corrections.

Most bugs in this project arrive as a screenshot of one wrong line. This
applies those one at a time, with the checks the box actually enforces, so a
fix cannot introduce the next bug.

It edits IN PLACE: the row is written over its own slot and NUL-padded to the
slot's end, so no pointer moves and nothing else in the record shifts. A row
that no longer fits is refused rather than relocated - if a correction needs
more room than the original had, that is worth knowing about rather than
silently working around.

Corrections live in analysis/row_fixes.json:

    [{"rec": 132, "off": "0x015620",
      "was": "Kazuki\\npeople of Io, make sure you take\\ndown Teral!\\"!\\"",
      "text": "Kazuki\\n\\u300cI'm counting on you, ...",
      "why": "lost its first line; doubled terminator; named the wrong target"}]

`was` is required and must match the row currently on disc. That is the whole
safety mechanism: if an earlier pass already changed the row, the text on disc
will not match and the fix is refused instead of overwriting work.

Usage: fix_row.py <iso> [--write]
"""
import hashlib
import io
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXES = os.path.join(ROOT, "analysis", "row_fixes.json")
WIDTH, MAXLINES = 34, 3
KAGI = u"「"


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def check(text):
    """The rules the engine enforces. Returns a complaint, or None."""
    lines = text.split("\n")
    body = lines[1:]
    if len(body) > MAXLINES:
        return "%d body lines, max %d" % (len(body), MAXLINES)
    for i, l in enumerate(body):
        if cols(l) > WIDTH:
            return "body line %d is %d columns, max %d" % (i + 1, cols(l), WIDTH)
    try:
        text.encode("cp932")
    except UnicodeEncodeError as e:
        return "not encodable as cp932: %s" % e
    if text.count(KAGI) > 1:
        return "more than one opening quote bracket"
    return None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    if not os.path.exists(FIXES):
        raise SystemExit("no %s - create it as a JSON list; the format is in "
                         "this file's docstring" % FIXES)
    fixes = json.load(io.open(FIXES, encoding="utf-8"))
    if not fixes:
        print("analysis/row_fixes.json is empty - nothing to do.")
        print("Add an entry per row you want to change; see the docstring.")
        return 0

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))

    edited, applied, bad = {}, 0, []
    for fx in fixes:
        rec = int(fx["rec"])
        off = int(str(fx["off"]), 0)
        eb = bytearray(edited.get(rec, items[rec][1]))
        z = bytes(eb).find(b"\x00", off)
        if z <= off:
            bad.append((rec, off, "no string at that offset"))
            continue
        cur = bytes(eb[off:z]).decode("cp932", "replace")
        if cur != fx["was"]:
            bad.append((rec, off, "row on disc does not match `was` - already "
                                  "changed? got %r" % cur[:48]))
            continue
        why = check(fx["text"])
        if why:
            bad.append((rec, off, why))
            continue
        nb = fx["text"].encode("cp932")
        k = z
        while k < len(eb) and eb[k] == 0:
            k += 1
        if len(nb) >= k - off:
            bad.append((rec, off, "needs %d bytes, slot holds %d"
                        % (len(nb) + 1, k - off)))
            continue
        eb[off:k] = nb + b"\x00" * (k - off - len(nb))
        edited[rec] = bytes(eb)
        applied += 1
        print("  rec%-4d %#08x  %s" % (rec, off, fx.get("why", "")))
        for l in fx["text"].split("\n"):
            print("            %-38r %d cols" % (l, cols(l)))

    print("\napplied %d, rejected %d" % (applied, len(bad)))
    for r, o, m in bad:
        print("   REJECT rec%-4d %#08x  %s" % (r, o, m))
    if bad or not write or not edited:
        if bad:
            print("\nREFUSING to write while any fix is rejected")
        elif not write:
            print("\n(dry run - pass --write to apply)")
        return 1 if bad else 0

    cdir = os.path.join(ROOT, "analysis", "_lzcache")
    if not os.path.isdir(cdir):
        os.makedirs(cdir)
    for rec, plain in edited.items():
        hdr = items[rec][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        key = os.path.join(cdir, "%s.lz" % hashlib.sha1(plain).hexdigest())
        if os.path.exists(key):
            blob = open(key, "rb").read()
        else:
            blob = banlz.compress_record(plain)
            if len(blob) > nxt - hdr:
                blob = banlz.compress_record_optimal(plain)
            open(key, "wb").write(blob)
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % rec
        print("   rec%-4d %d bytes (slot %d)" % (rec, len(blob), nxt - hdr))
        sys.stdout.flush()
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for rec, plain in edited.items():
        assert bytes(chk[rec][1]) == plain, "readback mismatch rec %d" % rec
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
