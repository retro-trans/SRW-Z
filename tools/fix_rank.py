# -*- coding: utf-8 -*-
"""\u51c6\u5c06 (Brigadier General) ships six different ways across 131 rows:
General 79, Colonel 20, Vice Admiral 12, Brigadier General 10, Major General 6,
Commodore 4. Agents keep fixing it one row at a time; this settles it.

English military usage splits two cases, so we keep both:
  \u300c\u30a8\u30fc\u30c7\u30eb\u51c6\u5c06\u300d as direct address -> "General Edel"
      (a brigadier general IS addressed as "General" - not a shortening)
  standalone \u51c6\u5c06 stating the rank    -> "Brigadier General"

GUARD: a row is skipped when it also contains another rank (\u5927\u4f50/\u4e2d\u4f50/\u5c11\u4f50/
\u5927\u5c09/\u4e2d\u5c09/\u5c11\u5c09/\u5143\u5e25/\u5c06\u8ecd), because then "Colonel" or "Captain" may
legitimately belong to a DIFFERENT character in the same line.

Usage: fix_rank.py <iso> [--write]
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
JUNSHOU = u"\u51c6\u5c06"
OTHER_RANKS = [u"\u5927\u4f50", u"\u4e2d\u4f50", u"\u5c11\u4f50", u"\u5927\u5c09",
               u"\u4e2d\u5c09", u"\u5c11\u5c09", u"\u5143\u5e25", u"\u5c06\u8ecd"]
WRONG = ("Vice[- ]Admiral|Rear Admiral|Admiral|Commodore|Major General"
         "|Brigadier General|Adjutant General|Colonel")


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def wrap(body):
    out, cur = [], ""
    for t in body.split(" "):
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


def retitle(s):
    # rank immediately followed by a capitalised name -> address form
    s = re.sub(r"\b(?:%s)\s+([A-Z][a-z]+)" % WRONG, r"General \1", s)
    # "the <rank>" / bare rank stating the rank itself
    s = re.sub(r"\bthe (?:%s)\b" % WRONG, "the Brigadier General", s)
    s = re.sub(r"\b(?:Vice[- ]Admiral|Commodore|Major General)\b",
               "Brigadier General", s)
    return s


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
            if JUNSHOU not in r["jp"]:
                continue
            if any(k in r["jp"] for k in OTHER_RANKS):
                skipped.append((rec, r["row"], "row names another rank too"))
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
            new = retitle(cur)
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

    print("rows retitled: %d in %d records" % (total, len(byrec)))
    for s in skipped[:10]:
        print("   SKIP rec%-4d row %-5d %s" % s)
    if len(skipped) > 10:
        print("   ... %d more skipped" % (len(skipped) - 10))
    if "--write" not in sys.argv:
        for rec, fx in sorted(byrec.items()):
            for x in fx[:3]:
                print("   rec%d row %d: %s" % (rec, x["row"],
                                               x["en"].replace("\n", " | ")))
        return
    for rec, fx in sorted(byrec.items()):
        q = os.path.join(FIX, "rec%03d_rank.json" % rec)
        io.open(q, "w", encoding="utf-8").write(
            json.dumps(fx, ensure_ascii=False, indent=0))
        print("wrote %s (%d)" % (os.path.basename(q), len(fx)))


if __name__ == "__main__":
    main()
