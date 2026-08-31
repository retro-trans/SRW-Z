# -*- coding: utf-8 -*-
"""Build the proofreading worklist: every dialogue row, japanese beside english.

One sheet per STAGE record, rows in script order so a proofreader reads the
scene as it plays rather than as a bag of strings. The japanese comes from the
pristine disc and is paired to the english THROUGH THE ROW POINTERS, the same
way rename_term.py does it - not by offset, which drifts, and not by index,
which breaks the moment a record gains or loses a row.

WHY THE KEY IS A HASH OF THE JAPANESE

Offsets move. 0.8.110 relocated rows and repointed them; later passes trimmed
text in place. Any key built from a byte offset is stale by the time a
translator sends work back. The japanese never changes, so
`rec:sha1(jp)[:12]:occurrence` survives every rebuild. srvc_en_by_hash.json
already uses this trick for the battle captions.

The occurrence index matters: the same japanese line genuinely appears more
than once, both within a record and across routes.

BUDGETS ARE EXPORTED, NOT ASSUMED

A proofreader who cannot see the limits will write lines that cannot be
applied. Every row carries its slot size, the bytes it currently uses, the
bytes free, its widest line in columns and its line count. The box is 3 lines
of 30 columns; over either and the row is refused on import - a row one column
too wide is what crashed every build from v1.55 to 0.8.104.

Usage: export_proofread.py <patched-iso> <pristine-iso> [--out DIR]
"""
import hashlib
import io
import json
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
NL = chr(10)
KAGI = chr(0x300C)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAXLINES, WIDTH = 3, 34


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SECTOR)
    d = banlz.decompress_all(f.read(SIZE))
    f.close()
    return d


def pair(eb, jb):
    """english offset -> japanese offset, through the record's pointer table."""
    out = {}
    for p in range(0, min(len(eb), len(jb)) - 4, 4):
        ve = struct.unpack_from("<I", eb, p)[0] - BASE
        vj = struct.unpack_from("<I", jb, p)[0] - BASE
        if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in out:
            out[ve] = vj
    return out


def text_at(b, off):
    z = b.find(b"\x00", off)
    if z <= off:
        return None, 0
    k = z
    while k < len(b) and b[k] == 0:
        k += 1
    try:
        return b[off:z].decode("cp932"), k - off
    except UnicodeDecodeError:
        return None, 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    iso, pristine = args[0], args[1]
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(ROOT, "analysis", "proofread"))
    if not os.path.isdir(out):
        os.makedirs(out)
    en, jp = load(iso), load(pristine)

    books, seen_total, unpaired = {}, 0, 0
    for ri in range(len(en)):
        if en[ri][1] is None or jp[ri][1] is None:
            continue
        eb, jb = bytes(en[ri][1]), bytes(jp[ri][1])
        m = pair(eb, jb)
        occ, rows = {}, []
        for off in sorted(m):
            et, slot = text_at(eb, off)
            if not et or NL not in et or KAGI not in et:
                continue
            jt, _ = text_at(jb, m[off])
            if not jt:
                unpaired += 1
                continue
            h = hashlib.sha1(jt.encode("cp932", "ignore")).hexdigest()[:12]
            n = occ.get(h, 0)
            occ[h] = n + 1
            body = et.split(NL)[1:]
            rows.append({
                "key": "%d:%s:%d" % (ri, h, n),
                "speaker": et.split(NL)[0],
                "jp": jt,
                "en": et,
                "slot": slot,
                "used": len(et.encode("cp932")),
                "free": slot - 1 - len(et.encode("cp932")),
                "cols": max([cols(l) for l in body] or [0]),
                "lines": len(body),
            })
        if rows:
            books[ri] = rows
            seen_total += len(rows)

    io.open(os.path.join(out, "dialogue.json"), "w", encoding="utf-8",
            newline=NL).write(json.dumps(books, ensure_ascii=False))
    print("records with dialogue : %d" % len(books))
    print("rows exported         : %d" % seen_total)
    print("rows with no japanese : %d" % unpaired)
    dup = sum(1 for rs in books.values() for r in rs if r["key"].endswith(":1"))
    print("rows that are a repeat of an earlier japanese line: %d" % dup)
    over = [r for rs in books.values() for r in rs
            if r["cols"] > WIDTH or r["lines"] > MAXLINES]
    print("rows ALREADY over the box (%d cols / %d lines): %d"
          % (WIDTH, MAXLINES, len(over)))
    print("wrote %s" % os.path.join(out, "dialogue.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
