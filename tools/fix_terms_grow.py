# -*- coding: utf-8 -*-
"""Term fixes whose replacement is LONGER than the text it replaces.

fix_terms_pass.py can only shrink a row in place. This one emits fixes JSON in
apply_fixes format instead, re-wrapping the body to 34 columns, so apply_fixes
handles option-3 relocation and validation. Rows are resolved through the
pointer, so relocated rows are covered too.

Each rule is conditioned on the Japanese so nothing unrelated is renamed.

Usage: fix_terms_grow.py <iso> [--write]
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
TAG = "names"

# (japanese key, wrong english, canonical english)
# Canon: getterrobo.fandom.com - General Hidler, Emperor Burai.
RULES = [
    # 総統 = Gattler's title (God Sigma). Shipped 4 ways: Fuhrer 17,
    # Chancellor 3, President 3, Fuehrer 1. No english source exists, so
    # "Supreme Commander" was chosen: unambiguous, and avoids applying
    # a Nazi association inconsistently across a villain's title.
    (u"総統", "Fuehrer", "Supreme Commander"),
    (u"総統", "Fuhrer", "Supreme Commander"),
    (u"総統", "Chancellor", "Supreme Commander"),
    (u"総統", "President", "Supreme Commander"),
    # νガンダム is Amuro's Nu Gundam. "v Gundam" is an ASCII
    # substitution for the greek nu, and reads as Victory Gundam - which is
    # not even in this game. Grows by one char, so it needs the rewrap pass.
    (u"νガンダム", "v Gundam", "Nu Gundam"),
    (u"\u30d2\u30c9\u30e9\u30fc", "Hydler", "Hidler"),
    (u"\u30d2\u30c9\u30e9\u30fc", "Hydra", "Hidler"),
    (u"\u30d6\u30e9\u30a4", "Bray", "Burai"),
    (u"\u30d6\u30e9\u30a4", "Brya", "Burai"),
    (u"ブライ", "Brai", "Burai"),   # 27 rows; Brai never matches Bright
    (u"百鬼", "Mykene", "Hyakki"),      # survivor the shrink pass missed
    (u"鉄甲鬼", "Tekkaki", "Tekkouki"),
    (u"鉄甲鬼", "Iron Demon", "Tekkouki"),
    (u"ツィーネ", "Tine", "Ziene"),
    (u"ギンガナム", "Ginganam", "Ghingnham"),
    (u"シュラン", "Shran", "Shuran"),
    (u"ディアナ", "Diana", "Dianna"),
    # Gaiking names - undocumented in English, decided for consistency:
    # アフロディア Aphrodia (matches Aphrodite), スカルムーン Skull Moon
    # as two words, ガガーン Gagaan keeping the long vowel.
    (u"アフロディア", "Afrodia", "Aphrodia"),
    (u"スカルムーン", "Skullmoon", "Skull Moon"),
    (u"ガガーン", "Gagan", "Gagaan"),
    (u"ガガーン", "Gaga", "Gagaan"),
]


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
            pairs = [(w, g) for k, w, g in RULES if k in r["jp"]]
            if not pairs:
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
            new = cur
            for w, g in pairs:
                new = re.sub(r"\b%s\b" % re.escape(w), g, new)
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

    print("rows changed: %d in %d records" % (total, len(byrec)))
    for s in skipped:
        print("   SKIP rec%-4d row %-5d %s" % s)
    if "--write" not in sys.argv:
        for rec, fx in sorted(byrec.items()):
            for x in fx[:3]:
                print("   rec%d row %d: %s" % (rec, x["row"],
                                               x["en"].replace("\n", " | ")))
        return
    for rec, fx in sorted(byrec.items()):
        p = os.path.join(FIX, "rec%03d_%s.json" % (rec, TAG))
        io.open(p, "w", encoding="utf-8").write(
            json.dumps(fx, ensure_ascii=False, indent=0))
        print("wrote %s (%d)" % (os.path.basename(p), len(fx)))


if __name__ == "__main__":
    main()
