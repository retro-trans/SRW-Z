# -*- coding: utf-8 -*-
"""太極 shipped as "Taiji" in seven-plus rows across rec113. The canonical form
is Taikyoku, which is LONGER, so fix_terms_pass (shrink-only) cannot do it.

This emits fixes JSON in apply_fixes format instead, re-wrapping the body to 34
columns so the growth does not overrun the box. apply_fixes then handles
option-3 relocation and validation.

Usage: fix_taikyoku.py <iso> [--write]
"""
import glob
import io
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(WORK, "analysis", "review", "fixes")
O, C = u"\u300a", u"\u300b"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
WIDTH, MAXLINES = 34, 3
KANJI = u"\u592a\u6975"          # 太極


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def wrap(body):
    """Greedy re-wrap; never splits a 《link》 across lines."""
    toks, out, cur = body.split(" "), [], ""
    for t in toks:
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

    byrec, total, skipped = {}, 0, []
    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        rows = json.load(io.open(p, encoding="utf-8"))
        jb, eb = bytes(jp[rec][1]), bytearray(items[rec][1])
        for r in rows:
            if KANJI not in r["jp"]:
                continue
            off = r["off"]
            nb4 = struct.pack("<I", BASE + r["off"])
            for i in range(0, len(jb) - 4, 4):
                if jb[i:i + 4] == nb4 and i + 4 <= len(eb):
                    v = struct.unpack_from("<I", bytes(eb), i)[0] - BASE
                    if 0 <= v < len(eb):
                        off = v
                    break
            e = off
            while e < len(eb) and eb[e] != 0:
                e += 1
            try:
                cur = bytes(eb[off:e]).decode("cp932")
            except UnicodeDecodeError:
                continue
            new = re.sub(r"\bTaiji\b", "Taikyoku", cur)
            if new == cur:
                continue
            lines = new.split("\n")
            if len(lines) < 2 or u"\u300c" not in cur:
                skipped.append((rec, r["row"], "not spoken dialogue"))
                continue
            body = wrap(" ".join(l.strip() for l in lines[1:]))
            if len(body) > MAXLINES:
                skipped.append((rec, r["row"], "%d lines after rewrap" % len(body)))
                continue
            if any(l.count(O) != l.count(C) for l in body):
                skipped.append((rec, r["row"], "link split"))
                continue
            byrec.setdefault(rec, []).append(
                {"row": r["row"], "en": "\n".join([lines[0]] + body)})
            total += 1

    print("rows with Taiji -> Taikyoku: %d in %d records" % (total, len(byrec)))
    for s in skipped:
        print("   SKIP rec%-4d row %-5d %s" % s)
    if "--write" not in sys.argv:
        for rec, fx in byrec.items():
            for x in fx[:4]:
                print("   rec%d row %d: %s" % (rec, x["row"],
                                               x["en"].replace("\n", " | ")))
        return
    for rec, fx in byrec.items():
        p = os.path.join(FIX, "rec%03d_taikyoku.json" % rec)
        io.open(p, "w", encoding="utf-8").write(
            json.dumps(fx, ensure_ascii=False, indent=0))
        print("wrote %s (%d)" % (os.path.basename(p), len(fx)))


if __name__ == "__main__":
    main()
