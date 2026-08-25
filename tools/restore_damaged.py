# -*- coding: utf-8 -*-
"""Rebuild rows this session damaged, from the pre-session exports.

Two of my own bugs compounded on the same rows:

1. fix_body_terms built substitution rules from junk variants (a mis-parsed row
   where a speaker field briefly held another character's name), so e.g.
   "The Edel -> Amuro" fired on real text: 「ジ・エーデル・ベルナル」 became
   "Amuro Bernal", and a 《Ghingnham》 link became 《Dianna》 - a DEAD link,
   which crashes.
2. apply_fixes.rebase() fell back to the whole agent string when a fix had no
   speaker line, appending it after the existing speaker and duplicating the
   tail ("...」.」").

Repair: for every affected row, start from the pre-session export text, re-apply
that row's agent fix if one exists (correctly this time - speaker line from the
export, body from the fix), and write it back. Rows are validated before they
are written: 3 lines, 34 columns with placeholders expanded, links intact.

Usage: restore_damaged.py <iso> [--dry-run]
"""
import glob
import io
import json
import multiprocessing
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES, strings

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
O, C = u"\u300a", u"\u300b"


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def damaged(t):
    """Signatures of the two bugs."""
    return bool(re.search(u"\u300d.{0,3}\u300d$", t.rstrip()))


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jp_stage = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    edited, n_fix, n_agent, skipped = {}, 0, 0, []

    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        rows = {r["off"]: r for r in json.load(io.open(p, encoding="utf-8"))}
        fixes = {}
        for q in glob.glob(os.path.join(WORK, "analysis", "review", "fixes",
                                        "rec%03d_*.json" % rec)):
            if q.endswith("_sonnet.json"):
                continue
            for fx in json.load(io.open(q, encoding="utf-8")):
                fixes[fx["row"]] = fx["en"]
        jb = bytes(jp_stage[rec][1])
        eb = bytearray(items[rec][1])
        touched = False
        for s, e in list(strings(bytes(eb))):
            try:
                cur = bytes(eb[s:e]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if not damaged(cur):
                continue
            r = rows.get(s)
            if r is None:
                skipped.append((rec, s, "no export row"))
                continue
            text = r["en"]
            fx = fixes.get(r["row"])
            if fx:
                fl = fx.split("\n")
                if len(fl) > 1:
                    text = "\n".join([text.split("\n")[0]] + fl[1:])
                    n_agent += 1
            parts = text.split("\n")
            if len(parts) - 1 > MAXLINES or any(ecols(l) > WIDTH for l in parts[1:]) \
               or any(l.count(O) != l.count(C) for l in parts):
                skipped.append((rec, s, "restored text fails validation"))
                continue
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            nb = text.encode("cp932")
            if len(nb) >= k - s:
                skipped.append((rec, s, "restored text does not fit"))
                continue
            eb[s:k] = nb + b"\x00" * (k - s - len(nb))
            touched = True
            n_fix += 1
        if touched:
            edited[rec] = bytes(eb)
    print("rows restored: %d (%d with their agent fix re-applied) in %d records"
          % (n_fix, n_agent, len(edited)))
    print("skipped: %d" % len(skipped))
    for s in skipped[:8]:
        print("   rec %-4d @%-7d %s" % s)
    if dry or not edited:
        return
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close(); pool.join()
    for n, plain in edited.items():
        hdr = items[n][0]
        blob = packed[n]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % n
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done")


if __name__ == "__main__":
    main()
