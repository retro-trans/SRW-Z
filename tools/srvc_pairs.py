# -*- coding: utf-8 -*-
"""Pair every battle caption to its japanese, through the sequence records.

Captions have resisted pairing all along, and every shortcut has been wrong:

  * same file offset          - SRVC was rebuilt, offsets moved
  * same index within a block - blocks gained and lost strings (block 267 has
                                3,005 japanese strings against 3,016 english),
                                so the drift is real and varies per block
  * nearest neighbour by eye  - works for one line, not for 18,700

The records already hold the answer. Each 8-byte cell is
[u16 clip_id][u16 section][u16 f2][00 00], and f2 resolves to a string INDEX
within the block. The cells themselves do not move: srvc_apply rewrites f2 in
place. So the cell at a given offset names the japanese string index in the
original and the english string index in ours - that is the mapping, taken from
the game's own data instead of inferred.

Writes analysis/caption_pairs.json (gitignored - it holds the japanese).

Usage: srvc_pairs.py <patched-iso> [out.json]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc
import srvc_records

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTOR = 2048
SEG_LBA, SRVC_LBA, SRVC_LEN = 1309609, 1313214, 2913887
OUT = os.path.join(ROOT, "analysis", "caption_pairs.json")


def main():
    iso = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    orig = open(os.path.join(ROOT, "extracted", "BTL_SRVC.BIN"), "rb").read()
    oseg = srvc.read_seg(open(os.path.join(ROOT, "extracted",
                                           "BTL_SRVC.SEG"), "rb").read())
    f = open(iso, "rb")
    f.seek(SRVC_LBA * SECTOR)
    cur = f.read(SRVC_LEN)
    f.seek(SEG_LBA * SECTOR)
    nseg = srvc.read_seg(f.read(len(oseg) * 4))
    f.close()

    ob = srvc.parse(orig, oseg)
    nb = srvc.parse(cur, nseg)
    A, _ = srvc_records.resolve(ob)
    B, _ = srvc_records.resolve(nb)

    pairs, n, skipped = [], 0, 0
    for bi in sorted(set(A) & set(B)):
        a = {r[0]: r[1] for r in A[bi]}          # cell offset -> jp string index
        b = {r[0]: r[1] for r in B[bi]}          # cell offset -> en string index
        ja, ea = ob[bi].strings, nb[bi].strings
        for cell in sorted(set(a) & set(b)):
            ji, ei = a[cell], b[cell]
            if ji >= len(ja) or ei >= len(ea):
                skipped += 1
                continue
            try:
                jt = ja[ji].decode("cp932")
                et = ea[ei].decode("cp932")
            except Exception:
                skipped += 1
                continue
            if not jt.strip() or not et.strip():
                continue
            pairs.append({"b": bi, "c": cell, "jp": jt, "en": et})
            n += 1
    # one entry per DISTINCT japanese/english pair - the same line is stored
    # once per unit that speaks it, and reading it 9 times is wasted effort
    seen, uniq = set(), []
    for p in pairs:
        k = (p["jp"], p["en"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"note": "battle captions paired through the sequence "
                            "records; contains japanese, do not publish",
                    "pairs": uniq}, ensure_ascii=False, indent=0))
    print("cells paired : %d" % n)
    print("distinct pairs: %d" % len(uniq))
    print("skipped       : %d" % skipped)
    print("wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
