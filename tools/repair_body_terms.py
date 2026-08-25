# -*- coding: utf-8 -*-
"""Undo the bad substitutions fix_body_terms.py made.

MY BUG, not an agent's. fix_body_terms built its "wrong -> canonical" rules from
analysis/names/groups.json, which lists EVERY English spelling a Japanese
speaker has ever shipped under - including junk from mis-parsed rows where the
speaker field briefly held a different character's name. "Ghingnham -> Dianna"
was built from ONE such line, and then fired on every row whose Japanese
mentions ディアナ, rewriting real occurrences of Ghingnham - including inside a
《Ghingnham》 glossary link (making it dead: an instant crash) and inside
speaker lines, so a row where Ghingnham talks ABOUT Dianna became Dianna
talking.

Repair: for every row a low-evidence rule could have touched, align the current
text word-by-word against the pre-pass export and restore any word the rule
flipped. Alignment (rather than blind replace) keeps legitimate occurrences of
the canonical name and survives rows that an agent also edited.

Usage: repair_body_terms.py <iso> [--dry-run]
"""
import glob
import io
import json
import multiprocessing
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNSAFE = {"Kei", "Ray", "Rey", "Gain", "Boss", "Four", "Jun", "Mome", "Dove",
          "Hap", "Blume", "Chiru", "Maaie", "Eina", "Bask", "Jie", "T Bone"}


def bad_rules():
    m = json.load(io.open(os.path.join(WORK, "analysis", "names", "map.json"), encoding="utf-8"))
    groups = {g["jp"]: g for g in json.load(io.open(
        os.path.join(WORK, "analysis", "names", "groups.json"), encoding="utf-8"))}
    canon = {e["canonical"] for e in m}
    out = []
    for e in m:
        jp, can = e["jp"], e["canonical"]
        if can in UNSAFE or len(can) < 4:
            continue
        for v, n in groups.get(jp, {}).get("variants", {}).items():
            if v == can or len(v) < 4 or v in UNSAFE:
                continue
            if not re.match(r"^[A-Za-z][A-Za-z .'-]*$", v):
                continue
            if v in canon and n < 10:
                out.append((jp, v, can))
    return out


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    rules = bad_rules()
    jp_stage = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    edited, n_rows, n_words = {}, 0, 0

    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        rows = json.load(io.open(p, encoding="utf-8"))
        jb = bytes(jp_stage[rec][1])
        eb = bytearray(edited.get(rec, items[rec][1]))
        touched = False
        for r in rows:
            pairs = [(v, can) for jp, v, can in rules
                     if jp in r["jp"] and re.search(r"\b%s\b" % re.escape(v), r["en"])]
            if not pairs:
                continue
            # where does this row live now?
            off = r["off"]
            nb4 = struct.pack("<I", BASE + r["off"])
            for i in range(0, len(jb) - 4, 4):
                if jb[i:i + 4] == nb4 and i + 4 <= len(eb):
                    v2 = struct.unpack_from("<I", bytes(eb), i)[0] - BASE
                    if 0 <= v2 < len(eb):
                        off = v2
                    break
            e = off
            while e < len(eb) and eb[e] != 0:
                e += 1
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            try:
                cur = bytes(eb[off:e]).decode("cp932")
            except UnicodeDecodeError:
                continue
            old_words, cur_words = r["en"].split(" "), cur.split(" ")
            if len(old_words) != len(cur_words):
                continue                      # row was rewritten; skip, report
            changed = False
            for i, (ow, cw) in enumerate(zip(old_words, cur_words)):
                for wrong, right in pairs:
                    if ow.replace(right, wrong) == cw.replace(right, wrong) and wrong in ow and right in cw:
                        cur_words[i] = cw.replace(right, wrong)
                        changed = True
                        n_words += 1
            if not changed:
                continue
            nt = " ".join(cur_words)
            nb = nt.encode("cp932")
            if len(nb) > k - off:
                continue
            eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            touched = True
            n_rows += 1
        if touched:
            edited[rec] = bytes(eb)
    print("rows repaired: %d (%d words restored) across %d records"
          % (n_rows, n_words, len(edited)))
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
