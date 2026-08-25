# -*- coding: utf-8 -*-
"""Rename a glossary term everywhere it appears, safely.

相克界 shipped as "Overlap" - a term I invented - when the established English
rendering is "Rivalry Zone" (MNeidengard's SRW Z import walkthrough, whose
definition matches the in-game entry: "a layer of distortion in the atmosphere
... time-space instability within makes passage impossible ... responsible for
a greenhouse effect"). Project rule: an established English term from the wiki
or an existing guide beats anything I derive myself.

Renaming a LINKED term is not a search-and-replace. The popup entry title and
the 《term》 in dialogue must match EXACTLY or the link is dead, and a dead link
crashes the game - so title and links are rewritten in the same pass, and the
result is re-verified.

Longer text also re-wraps: "Rivalry Zone" is 5 bytes longer than "Overlap", so
lines are re-flowed (links glued so they never straddle a break) and relocated
when they outgrow their slot.

Usage: rename_term.py <iso> <old> <new> [--dry-run]
"""
import multiprocessing
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from fix_popup_wrap import sstrings
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

BASE = 0x7566F0
O, C, GLUE = u"\u300a", u"\u300b", u"\ue000"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return cols(s)


def wrap(flat):
    glued = re.sub(O + u"(.*?)" + C,
                   lambda m: O + m.group(1).replace(u" ", GLUE) + C, flat)
    toks, lines, cur = glued.split(" "), [], []
    for t in toks:
        if cur and ecols(" ".join(cur + [t])) > WIDTH:
            lines.append(cur)
            cur = [t]
        else:
            cur = cur + [t]
    if cur:
        lines.append(cur)
    return [u" ".join(l).replace(GLUE, u" ") for l in lines]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
    dry = "--dry-run" in sys.argv
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    edited, st = {}, {"title": 0, "body": 0, "reloc": 0, "skip": 0}

    for idx, (hdr, dec) in enumerate(items):
        if dec is None or old.encode("cp932") not in bytes(dec):
            continue
        eb = bytearray(dec)
        # walk strings from the END so earlier offsets stay valid
        for off, s in sorted(sstrings(bytes(eb)), key=lambda t: -t[0]):
            if old.encode("cp932") not in s:
                continue
            try:
                t = s.decode("cp932")
            except UnicodeDecodeError:
                continue
            e = off + len(s)
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            if "\n" not in t:                       # a popup title
                nt = t.replace(old, new)
                st["title"] += 1
            else:
                parts = t.replace(old, new).split("\n")
                name, bodyl = parts[0], parts[1:]
                if len(bodyl) > MAXLINES or any(ecols(l) > WIDTH for l in bodyl):
                    bodyl = wrap(u" ".join(bodyl))
                if len(bodyl) > MAXLINES or any(ecols(l) > WIDTH for l in bodyl):
                    st["skip"] += 1
                    continue
                nt = u"\n".join([name] + bodyl)
                st["body"] += 1
            nb = nt.encode("cp932")
            if len(nb) < k - off:
                eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op, npp = struct.pack("<I", BASE + off), struct.pack("<I", BASE + new_off)
                cnt, j = 0, 0
                while True:
                    j = eb.find(op, j)
                    if j < 0:
                        break
                    if j % 4 == 0:
                        eb[j:j + 4] = npp
                        cnt += 1
                        j += 4
                    else:
                        j += 1
                if cnt < 1:
                    del eb[new_off:]
                    st["skip"] += 1
                    continue
                for x in range(off, k):
                    eb[x] = 0
                st["reloc"] += 1
            edited[idx] = bytes(eb)
    print("titles %d | body strings %d | relocated %d | skipped %d"
          % (st["title"], st["body"], st["reloc"], st["skip"]))
    print("records to rebuild: %d" % len(edited))
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
    changed = sorted(o for o in before if check[o] != before[o])
    assert set(changed) <= set(items[n][0] for n in edited), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed" % len(changed))


if __name__ == "__main__":
    main()
