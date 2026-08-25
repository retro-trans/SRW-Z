# -*- coding: utf-8 -*-
"""Consolidated STAGE renames, applied in ONE pass, length-preserving.

Must be a real file, not a heredoc: multiprocessing on Windows re-imports the
module in each spawned worker, and a heredoc script has no importable path
(OSError: Invalid argument: '<stdin>').

Every replacement here is the SAME BYTE LENGTH or shorter, and each string is
rewritten inside its own NUL-terminated slot with the slack re-padded, so no
offset in the record moves. Verify with tools/verify_pointers.py afterwards.

A glossary term and its <<term>> links are ONE edit. Renaming the keyword bank
without the dialogue links (or vice versa) leaves a dead link, and a dead link
CRASHES the scene. The Ref -> Lifting rename below exists because the library
rebuild already renamed that bank entry.

Usage: fix_stage_batch.py <iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"
O, C = u"《", u"》"
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}

# (pattern, replacement, why). Word-bounded, applied to DECODED text.
RULES = [
    (u"《Ref》", u"《Lifting》",
     "the library bank now says Lifting; this link would otherwise be DEAD"),
    (r"\bShuran\b", "Schlan",
     "wiki/German naming theme (Schlange); owner-confirmed. 6 chars -> 6 chars"),
    (r"\bLogos\b", "LOGOS",
     "glossary DB says LOGOS; the bank entry moves with it. 5 -> 5"),
    (r"\bKashmar\b", "Kashmir",
     "same character as Kashmir Valle; 7 -> 7"),
]


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


def fix_record(data):
    buf = bytearray(data)
    hits = {}
    skipped = []
    i, n = 0, len(buf)
    while i < n:
        j = buf.find(NUL, i)
        if j == -1:
            j = n
        seg = bytes(buf[i:j])
        if seg:
            try:
                s = seg.decode("cp932")
            except Exception:
                i = j + 1
                continue
            new = s
            for pat, rep, _ in RULES:
                new, k = re.subn(pat, rep, new)
                if k:
                    hits[pat] = hits.get(pat, 0) + k
            if new != s:
                # a link rename can push the line past the box - re-wrap
                lines = new.split("\n")
                if len(lines) > 1 and u"「" in new:
                    body = " ".join(l.strip() for l in lines[1:])
                    body = " ".join(body.split())
                    out = wrap(body)
                    if len(out) <= MAXLINES and all(
                            l.count(O) == l.count(C) for l in out):
                        new = "\n".join([lines[0]] + out)
                enc = new.encode("cp932")
                e = j
                while e < n and buf[e] == 0:
                    e += 1
                if len(enc) <= e - i:
                    buf[i:e] = enc + NUL * (e - i - len(enc))
                else:
                    skipped.append((i, len(enc), e - i))
                    for pat, _, _ in RULES:
                        hits.pop(pat, None)
        i = j + 1
    return bytes(buf), hits, skipped


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, total, allskip = {}, {}, []
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        new, hits, skipped = fix_record(data)
        allskip += [(idx,) + s for s in skipped]
        if hits:
            edited[idx] = new
            for k, v in hits.items():
                total[k] = total.get(k, 0) + v

    print("records touched: %d" % len(edited))
    for pat, rep, why in RULES:
        print("   %-18s -> %-12s %5d   (%s)" % (pat, rep, total.get(pat, 0), why))
    if allskip:
        print("SKIPPED (would not fit): %d" % len(allskip))
        for s in allskip[:6]:
            print("   rec%-4d needs %d, slot %d" % s)
    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return

    import multiprocessing
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close()
    pool.join()
    for idx, plain in edited.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw))
             if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written")


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


if __name__ == "__main__":
    main()
