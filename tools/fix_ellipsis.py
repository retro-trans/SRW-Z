# -*- coding: utf-8 -*-
"""Normalise ellipses in the DeepSeek-translated records.

2,596 dialogue rows use a two-dot ".." (3,110 occurrences) and 127 use the
fullwidth "…" that our own encoding rule forbids. The two-dot form is almost
certainly the byte-budget trimmer having dropped a dot to save one byte, back
when rows could not grow; option-3 relocation removed that constraint.

Rows are located by RE-RESOLVING the pointer at apply time rather than trusting
a previously exported offset, so this stays correct even after other passes
have relocated rows.

Rows that no longer fit are re-wrapped (placeholder-aware, links glued); rows
that outgrow their slot are relocated - appended to the record with every
4-aligned pointer rewritten and the old slot zeroed.

Usage: fix_ellipsis.py <iso> [--dry-run]
"""
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
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(WORK, "analysis", "review")
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


def fix_text(en):
    return re.sub(r"(?<!\.)\.\.(?!\.)", "...", en).replace(u"\u2026", "...")


def ptr_map(jb):
    ptr = {}
    for i in range(0, len(jb) - 4, 4):
        v = struct.unpack_from("<I", jb, i)[0] - BASE
        if 0 <= v < len(jb):
            ptr.setdefault(v, []).append(i)
    return ptr


def resolve(jb, eb, ptr, off):
    """Where does the row at JP offset `off` live in our record now?"""
    for p in ptr.get(off, []):
        if p + 4 <= len(eb):
            v = struct.unpack_from("<I", eb, p)[0] - BASE
            if 0 <= v < len(eb):
                return v
    return off if off < len(eb) else None


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, st = {}, {"inplace": 0, "rewrap": 0, "reloc": 0, "skip": 0}
    for p in sorted(os.listdir(REV)):
        if not (p.startswith("rec") and p.endswith(".json")):
            continue
        n = int(p[3:6])
        rows = json.load(io.open(os.path.join(REV, p), encoding="utf-8"))
        jb, eb = bytes(jp[n][1]), bytearray(items[n][1])
        ptr = ptr_map(jb)
        touched = False
        for r in rows:
            if "\n" not in r["jp"] or len(r["jp"]) <= 10:
                continue
            off = resolve(jb, bytes(eb), ptr, r["off"] if False else r["off"])
            # r["off"] came from the same resolver; re-resolve from the JP row
            # offset when we can, so a later relocation cannot desync us.
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
            new = fix_text(cur)
            if new == cur:
                continue
            parts = new.split("\n")
            name, body = parts[0], parts[1:]
            if len(body) > MAXLINES or any(ecols(l) > WIDTH for l in body):
                body = wrap(" ".join(body))
                if len(body) > MAXLINES or any(ecols(l) > WIDTH for l in body):
                    st["skip"] += 1
                    continue
                st["rewrap"] += 1
            else:
                st["inplace"] += 1
            nt = u"\n".join([name] + body)
            nb = nt.encode("cp932")
            if len(nb) < k - off:
                eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                old_ptr = struct.pack("<I", BASE + off)
                new_ptr = struct.pack("<I", BASE + new_off)
                cnt, j = 0, 0
                while True:
                    j = eb.find(old_ptr, j)
                    if j < 0:
                        break
                    if j % 4 == 0:
                        eb[j:j + 4] = new_ptr
                        cnt += 1
                        j += 4
                    else:
                        j += 1
                if cnt < 1:
                    del eb[new_off:]
                    st["skip"] += 1
                    st["inplace" if st["inplace"] else "skip"] -= 0
                    continue
                for x in range(off, k):
                    eb[x] = 0
                st["reloc"] += 1
                st["inplace"] = max(0, st["inplace"] - 1)
            touched = True
        if touched:
            edited[n] = bytes(eb)
    print("rows fixed in place %d | re-wrapped %d | relocated %d | skipped %d"
          % (st["inplace"], st["rewrap"], st["reloc"], st["skip"]))
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
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot (%d > %d)" % (n, len(blob), nxt - hdr)
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(items[n][0] for n in edited), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
