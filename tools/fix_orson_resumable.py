# -*- coding: utf-8 -*-
u"""Resumable Orson->Olson (+ the rec72 Mizuki reword), one record at a time.

The batch version recompresses all 55 records and writes once at the end, so a
kill loses everything - and long jobs get killed in this environment before the
slow pure-Python optimal compressor finishes. This writes each record to the
image the instant it is compressed and flushes, so a kill loses at most the
record in flight. Re-running RESUMES: a record already converted has no "Orson"
left to find and is skipped.

Smallest records first, so the cheap ones all land before any timeout and only
the few slow giants remain for the next run.

Usage: fix_orson_resumable.py <iso>   (idempotent; run until it reports 0 left)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
REGIONS = [("STAGE", 1651029, 3910128, True),
           ("COMPDATA", 1823000, 74 * 2048, False)]
OLD, NEW = b"Orson", b"Olson"
KO, KC = b"\x81\x75", b"\x81\x76"
MIZ_OLD = b"Mizuki\n" + KO + b"Stubbornness gets tiring. In\nbattle, and about Touga and\nSandman." + KC
MIZ_NEW = b"Mizuki\n" + KO + b"Putting on a front is tiring. The\nwar, and Touga and Sandman too." + KC


def main():
    iso = sys.argv[1]
    f = open(iso, "r+b")
    remaining = 0
    for name, lba, size, is_stage in REGIONS:
        f.seek(lba * SEC)
        raw = f.read(size)
        live = [(h, bytearray(d)) for h, d in banlz.decompress_all(raw)
                if isinstance(h, int) and d is not None]
        heads = sorted(h for h, _ in live)
        # records needing work, smallest first
        todo = []
        for ri, (hdr, d) in enumerate(live):
            need = d.count(OLD) > 0
            if is_stage and MIZ_OLD in d:
                need = True
            if need:
                todo.append((len(d), ri, hdr))
        todo.sort()
        print("%s: %d record(s) still to convert" % (name, len(todo)))
        for _sz, ri, hdr in todo:
            d = live[ri][1]
            if is_stage and MIZ_OLD in d:
                k = d.find(MIZ_OLD)
                e = k + len(MIZ_OLD)
                while e < len(d) and d[e] == 0:
                    e += 1
                slot = e - k
                d[k:e] = MIZ_NEW + b"\x00" * (slot - len(MIZ_NEW))
            d[:] = d.replace(OLD, NEW)
            nxt = min([h for h in heads if h > hdr] or [len(raw)])
            room = nxt - hdr
            blob = banlz.compress_record(bytes(d))
            if len(blob) > room:
                blob = banlz.compress_record_optimal(bytes(d))
            assert len(blob) <= room, "rec%d over slot (%d>%d)" % (ri, len(blob), room)
            # write just this record's slot, in place
            f.seek(lba * SEC + hdr)
            f.write(blob + b"\x00" * (room - len(blob)))
            f.flush()
            os.fsync(f.fileno())
            print("  %s rec%-4d done (%d bytes)" % (name, ri, len(blob)))
        remaining += len(todo)
    f.close()
    print("\nconverted this run; re-run if any remain. total attempted: %d" % remaining)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
