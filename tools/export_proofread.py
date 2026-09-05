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
import reflow_dialogue as R   # width model + per-box-type classification

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
    """english offset -> (japanese offset, pointer position).

    The pointer POSITION is what orders the sheet. See ROW ORDER in the header:
    sorting by the text's own offset is storage order, which is not the order
    the scene plays.
    """
    out = {}
    for p in range(0, min(len(eb), len(jb)) - 4, 4):
        ve = struct.unpack_from("<I", eb, p)[0] - BASE
        vj = struct.unpack_from("<I", jb, p)[0] - BASE
        if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in out:
            out[ve] = (vj, p)
    return out


# WHAT COUNTS AS A DIALOGUE ROW
#
# This used to be "the english has a newline AND a 「". Stage 35 then had its
# corner brackets removed - they do nothing in the engine, and dropping them
# gives back 4 columns and 4 bytes a row - and the whole record disappeared
# from this export, because every row failed the 「 test. The sheet push then
# died on KeyError: '61'.
#
# The japanese is the fixed point: it is never edited, and every spoken line
# carries 「 there. So the bracket test belongs on the JAPANESE, which also
# keeps recap panels and help text out just as effectively.


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
    adv = R.load_adv(iso)   # half-width advance table for the proportional font

    books, seen_total, unpaired = {}, 0, 0
    for ri in range(len(en)):
        if en[ri][1] is None or jp[ri][1] is None:
            continue
        eb, jb = bytes(en[ri][1]), bytes(jp[ri][1])
        m = pair(eb, jb)
        bm = R.boxmap(bytearray(eb))   # offset -> 1 over-map(narrow) / 0 scene(wide)
        # KEYS ARE NUMBERED IN OFFSET ORDER, ROWS ARE DISPLAYED IN POINTER
        # ORDER. These must stay separate. The key is rec:sha1(jp):occurrence,
        # and the occurrence counter follows whatever order it is computed in -
        # so if it followed the display order, ":0" and ":1" would swap for any
        # japanese line appearing twice in a record, silently re-pointing work
        # already submitted against the old sheet at the wrong row. Offset order
        # is arbitrary but STABLE, which is the only property a key needs.
        occ, key_of = {}, {}
        for off in sorted(m):
            et, _slot = text_at(eb, off)
            if not et or NL not in et:
                continue
            jt, _ = text_at(jb, m[off][0])
            if not jt or KAGI not in jt:
                continue
            h = hashlib.sha1(jt.encode("cp932", "ignore")).hexdigest()[:12]
            n = occ.get(h, 0)
            occ[h] = n + 1
            key_of[off] = "%d:%s:%d" % (ri, h, n)

        rows = []
        for off in sorted(m, key=lambda o: m[o][1]):
            et, slot = text_at(eb, off)
            if not et or NL not in et:
                continue
            jt, _ = text_at(jb, m[off][0])
            if not jt or KAGI not in jt:
                unpaired += 1
                continue
            body = et.split(NL)[1:]
            over = bm.get(off, 1) == 1   # default over-map (narrow, safe)
            pxlimit = R.OVERMAP_PX if over else R.SCENE_PX
            widest = max([R.width(l.replace(KAGI, "").replace(chr(0x300D), ""), adv)
                          for l in body] or [0])
            rows.append({
                "key": key_of[off],
                "speaker": et.split(NL)[0],
                "jp": jt,
                "en": et,
                "slot": slot,
                "used": len(et.encode("cp932")),
                "free": slot - 1 - len(et.encode("cp932")),
                "cols": max([cols(l) for l in body] or [0]),
                "lines": len(body),
                "box": "over-map" if over else "scene",
                "px": widest,
                "pxlimit": pxlimit,
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
            if r["px"] > r["pxlimit"] or r["lines"] > MAXLINES]
    print("rows ALREADY over the box (px > box limit / %d lines): %d"
          % (MAXLINES, len(over)))
    print("wrote %s" % os.path.join(out, "dialogue.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
