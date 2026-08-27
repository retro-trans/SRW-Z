# -*- coding: utf-8 -*-
"""Find rows whose SPEAKER name disagrees with the japanese speaker field.

Found 2026-08-26 while fixing truncated rows: rec53 has ギンガナム labelled three
different ways in five consecutive rows - 'Ghingnham' (correct), 'Dianna' and
'Agrippa'. In each wrong case the label is the first character NAMED IN THE BODY
of that line, so a pass took the speaker from the sentence instead of the
speaker field.

No dictionary is needed to detect it. Group every row by its japanese speaker,
resolved through the pointer; the english label the group agrees on is the
mapping, and any row disagreeing with its own group is suspect. Rows are only
reported when the group is large enough to be confident and the majority is
overwhelming.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
MIN_GROUP = 8
MIN_SHARE = 0.90


def rows(iso):
    f = open(iso, "rb"); f.seek(LBA * SECTOR)
    en = banlz.decompress_all(f.read(SIZE)); f.close()
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())
    for idx in range(len(en)):
        e, j = en[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        e, j = bytes(e), bytes(j)
        seen = {}
        for p in range(0, min(len(e), len(j)) - 4, 4):
            ve = struct.unpack_from("<I", e, p)[0] - BASE
            vj = struct.unpack_from("<I", j, p)[0] - BASE
            if 0 <= ve < len(e) and 0 <= vj < len(j) and ve not in seen:
                seen[ve] = vj
        for eo, jo in seen.items():
            ze, zj = e.find(b"\x00", eo), j.find(b"\x00", jo)
            if ze <= eo or zj <= jo:
                continue
            try:
                se = e[eo:ze].decode("cp932")
                sj = j[jo:zj].decode("cp932")
            except Exception:
                continue
            if "\n" not in se or "\n" not in sj:
                continue
            yield idx, eo, se, sj


def main():
    iso = sys.argv[1]
    groups = collections.defaultdict(collections.Counter)
    rec = collections.defaultdict(list)
    for idx, eo, se, sj in rows(iso):
        nj = sj.split("\n", 1)[0]
        ne = se.split("\n", 1)[0]
        if not nj or nj.startswith("$"):
            continue
        groups[nj][ne] += 1
        rec[nj].append((idx, eo, ne, se, sj))

    suspects = []
    for nj, cnt in groups.items():
        tot = sum(cnt.values())
        if tot < MIN_GROUP:
            continue
        best, n = cnt.most_common(1)[0]
        if n / float(tot) < MIN_SHARE:
            continue
        for idx, eo, ne, se, sj in rec[nj]:
            if ne != best:
                body_jp = sj.split("\n", 1)[1]
                # the tell: the wrong label names someone spoken ABOUT
                suspects.append((nj, best, ne, idx, eo, se, body_jp))

    print("rows whose english speaker disagrees with its own group: %d\n"
          % len(suspects))
    by = collections.Counter((s[0], s[1], s[2]) for s in suspects)
    for (nj, best, ne), n in by.most_common(30):
        print("   %-12s should be %-18s shipped as %-18s %3d rows"
              % (nj, repr(best), repr(ne), n))
    if "--list" in sys.argv:
        print()
        for nj, best, ne, idx, eo, se, bj in suspects:
            print("rec%-4d %#08x  %s -> %s" % (idx, eo, repr(ne), repr(best)))
            print("     %r" % se.replace("\n", " | ")[:90])


if __name__ == "__main__":
    main()
