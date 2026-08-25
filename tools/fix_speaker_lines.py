# -*- coding: utf-8 -*-
"""77 rows lost their English speaker line and use ASCII " instead of kagi.

    JP   \u30b8\u30fb\u30a8\u30fc\u30c7\u30eb / \u300c\u3044\u3044\u3088\u3001\u305d\u3046\u3044\u3046\u306e\uff01 / ...   (speaker + 3 body)
    EN   "Fine, I like that! The more / ...        (NO speaker, ASCII quotes)

Both are player-visible: no nameplate, and the wrong quote glyphs. This was
mis-diagnosed as export "mispairing" for most of the project.

The English speaker label is recovered from the corpus itself: for the row's
japanese speaker tag, take the label used by the OTHER (intact) rows with the
same tag. That is reliable precisely because these rows are a small minority.

Emits apply_fixes JSON, so relocation and validation are handled there.

Usage: fix_speaker_lines.py <iso> [--write]
"""
import collections
import glob
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(WORK, "analysis", "review", "fixes")
KAGI_L, KAGI_R = u"\u300c", u"\u300d"
O, C = u"\u300a", u"\u300b"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
WIDTH, MAXLINES = 34, 3


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def wrap(body):
    """Re-wrap; damaged rows were written without a speaker line and some run
    past 34 columns, so a plain prepend is not enough."""
    out, cur = [], ""
    for t in body.split(" "):
        if not t:
            continue
        cand = t if not cur else cur + " " + t
        if ecols(cand) <= WIDTH:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = t
    if cur:
        out.append(cur)
    return out


def main():
    iso_path = sys.argv[1]
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(bytes(f.read(SIZE)))
    f.close()

    # learn tag -> english label from the intact rows
    label = collections.defaultdict(collections.Counter)
    allrows = []
    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        for r in json.load(io.open(p, encoding="utf-8")):
            allrows.append((rec, r))
            jl, el = r["jp"].split("\n"), r["en"].split("\n")
            if len(jl) >= 2 and len(el) >= 2 and KAGI_L in r["en"]:
                label[jl[0].strip()][el[0].strip()] += 1

    byrec, total, skipped = {}, 0, []
    for rec, r in allrows:
        jl, el = r["jp"].split("\n"), r["en"].split("\n")
        if KAGI_L not in r["jp"] or len(jl) < 2:
            continue
        broken = (len(el) < len(jl) and KAGI_L not in el[0]
                  and el[0].lstrip().startswith('"'))
        if not broken:
            continue
        tag = jl[0].strip()
        if not label[tag]:
            skipped.append((rec, r["row"], "no known label for the jp tag"))
            continue
        name = label[tag].most_common(1)[0][0]

        body = list(el)
        body[0] = body[0].lstrip()
        if body[0].startswith('"'):
            body[0] = KAGI_L + body[0][1:]
        if body[-1].rstrip().endswith('"'):
            body[-1] = body[-1].rstrip()[:-1] + KAGI_R
        # any stray ASCII quote left inside becomes nothing sensible - refuse
        if '"' in "\n".join(body):
            skipped.append((rec, r["row"], "unpaired ASCII quote left"))
            continue
        if len(body) > MAXLINES:
            skipped.append((rec, r["row"], "%d body lines" % len(body)))
            continue
        if any(ecols(l) > WIDTH for l in body):
            body = wrap(" ".join(l.strip() for l in body))
            if len(body) > MAXLINES or any(ecols(l) > WIDTH for l in body):
                skipped.append((rec, r["row"], "cannot fit after rewrap"))
                continue
        if any(l.count(O) != l.count(C) for l in body):
            skipped.append((rec, r["row"], "link split"))
            continue
        byrec.setdefault(rec, []).append(
            {"row": r["row"], "en": "\n".join([name] + body)})
        total += 1

    print("rows repaired: %d in %d records" % (total, len(byrec)))
    for s in skipped[:12]:
        print("   SKIP rec%-4d row %-5d %s" % s)
    if len(skipped) > 12:
        print("   ... %d more skipped" % (len(skipped) - 12))
    if "--write" not in sys.argv:
        for rec, fx in sorted(byrec.items())[:2]:
            for x in fx[:3]:
                print("   rec%d row %d: %s" % (rec, x["row"],
                                               x["en"].replace("\n", " | ")))
        return
    for rec, fx in sorted(byrec.items()):
        q = os.path.join(FIX, "rec%03d_spk.json" % rec)
        io.open(q, "w", encoding="utf-8").write(
            json.dumps(fx, ensure_ascii=False, indent=0))
        print("wrote %s (%d)" % (os.path.basename(q), len(fx)))


if __name__ == "__main__":
    main()
