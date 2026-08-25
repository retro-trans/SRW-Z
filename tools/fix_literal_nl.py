# -*- coding: utf-8 -*-
"""224 rows carry a LITERAL backslash-n instead of a real line break, so the
dialogue box shows the characters \n to the player:

    Cagalli\u300cSorry...\nAll I can do is\napologize...\u300d

Unescaping adds a display line, which can push the body past the 3-line limit,
so this rejoins the body and re-wraps it to 34 columns rather than substituting
in place. Emits apply_fixes JSON, which handles relocation and validation.

Usage: fix_literal_nl.py <iso> [--write]
"""
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
O, C = u"\u300a", u"\u300b"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
WIDTH, MAXLINES = 34, 3
BS = chr(92)
TARGET = BS + "n"


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def wrap(body):
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

    byrec, total, skipped = {}, 0, []
    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        jb, eb = bytes(jp[rec][1]), bytearray(items[rec][1])
        for r in json.load(io.open(p, encoding="utf-8")):
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
            if TARGET not in cur:
                continue
            lines = cur.split("\n")
            if len(lines) < 2 or u"\u300c" not in cur:
                skipped.append((rec, r["row"], "not spoken dialogue"))
                continue
            body = " ".join(l.strip() for l in lines[1:])
            body = body.replace(TARGET, " ")
            while "  " in body:
                body = body.replace("  ", " ")
            out = wrap(body.strip())
            if len(out) > MAXLINES:
                skipped.append((rec, r["row"], "%d lines after rewrap" % len(out)))
                continue
            if any(l.count(O) != l.count(C) for l in out):
                skipped.append((rec, r["row"], "link split"))
                continue
            byrec.setdefault(rec, []).append(
                {"row": r["row"], "en": "\n".join([lines[0]] + out)})
            total += 1

    print("rows with a literal backslash-n: %d in %d records" % (total, len(byrec)))
    for s in skipped[:12]:
        print("   SKIP rec%-4d row %-5d %s" % s)
    if len(skipped) > 12:
        print("   ... %d more skipped" % (len(skipped) - 12))
    if "--write" not in sys.argv:
        for rec, fx in sorted(byrec.items())[:3]:
            for x in fx[:2]:
                print("   rec%d row %d: %s" % (rec, x["row"],
                                               x["en"].replace("\n", " | ")))
        return
    for rec, fx in sorted(byrec.items()):
        q = os.path.join(FIX, "rec%03d_nl.json" % rec)
        io.open(q, "w", encoding="utf-8").write(
            json.dumps(fx, ensure_ascii=False, indent=0))
        print("wrote %s (%d)" % (os.path.basename(q), len(fx)))


if __name__ == "__main__":
    main()
