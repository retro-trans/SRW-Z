# -*- coding: utf-8 -*-
"""Apply single-line STAGE dialogue fixes IN PLACE (byte-safe, slot-preserving).

Never re-runs apply_stage.py (stale JP sources regress ~200 records - see
memory STAGE edit safety). Each fix locates its field by a UNIQUE substring of
the current English bytes, rewrites the field inside its own NUL-padded slot
(intra-record offsets untouched), recompresses only the touched records into
their fixed slots and verifies the record heads before writing.

Fix file: JSON list of [rec, "unique current substring", "full new field"].
The new field is the whole field including the speaker line and 「」, with
explicit line breaks (max 3 body lines). "$n" (protagonist) is stored literally.

Usage: fix_lines_inplace.py <iso> <fixes.json> [--write]
Then: verify_pointers.py --against iso/srwz.bin, export_proofread.py,
sheets_preserve.py, sheets_push.py --only <book>, and read a row back.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128


def main():
    iso, fixfile = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    fixes = json.load(open(fixfile, encoding="utf-8"))
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    en = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
          if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in en)
    touched = {}
    ok = True
    for ri, pat, new in fixes:
        pat = pat.encode("cp932")
        d = en[ri][1]
        i = d.find(pat)
        assert i >= 0 and d.find(pat, i + 1) < 0, "rec%d: pattern not unique/found: %r" % (ri, pat)
        s = d.rfind(b"\x00", 0, i) + 1
        z = d.find(b"\x00", i)
        e = z
        while e < len(d) and d[e] == 0:
            e += 1
        slot = e - s - 1
        nb = new.encode("cp932")
        lines = new.count("\n")
        fit = len(nb) <= slot and lines <= 3
        print("rec%d: old %d B, slot %d, new %d B, %d body lines -> %s"
              % (ri, z - s, slot, len(nb), lines, "OK" if fit else "NOFIT"))
        if not fit:
            ok = False
            continue
        d[s:s + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
        touched[ri] = d
    if not ok:
        sys.exit("some lines do not fit - nothing written")
    if not write:
        print("(dry run)")
        return
    for ri in sorted(touched):
        h = en[ri][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        dd = bytes(touched[ri])
        blob = banlz.compress_record(dd)
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(dd)
        assert len(blob) <= nxt - h, "rec%d over slot" % ri
        rt, _ = banlz.decompress_record(blob, 0)
        assert rt == dd
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    assert [hh for hh, x in banlz.decompress_all(bytes(raw))
            if isinstance(hh, int) and x is not None] == heads
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written: recs", sorted(touched))


if __name__ == "__main__":
    main()
