# -*- coding: utf-8 -*-
"""Revert a chosen set of STAGE records to japanese, for bisecting a crash.

bisect_build.py splits by FILE. When a crash is already pinned to STAGE, the
next question is WHICH RECORD, and 205 records need a binary search rather than
205 playthroughs. This reverts a half (or any explicit set) to the pristine
japanese text, leaving everything else ours: play to the crash point, and the
answer is whether it still happens.

    revert_records.py <iso> 0-102          first half
    revert_records.py <iso> 79             one record
    revert_records.py <iso> 0-50,60,70-80  any mix

The japanese record often compresses LARGER than our english (english is mostly
ASCII), so a revert can fail to fit the slot the english was written into. The
fast compressor is tried first and the optimal one only where it must be, since
optimal costs about 85 seconds per record.

Usage: revert_records.py <iso> <spec> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
JP_ISO = "iso/srwz.bin"


def parse(spec, n):
    want = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            want.update(range(int(a), int(b) + 1))
        else:
            want.add(int(part))
    return sorted(i for i in want if 0 <= i < n)


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def main():
    iso, spec = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv

    jp = [(h, d) for h, d in banlz.decompress_all(load(JP_ISO))
          if isinstance(h, int) and d is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    want = parse(spec, min(len(live), len(jp)))
    print("reverting %d record(s): %s%s"
          % (len(want), want[:12], " ..." if len(want) > 12 else ""))

    done = skipped = 0
    for ri in want:
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        room = nxt - hdr
        data = bytes(jp[ri][1])
        blob = banlz.compress_record(data)
        if len(blob) > room:
            blob = banlz.compress_record_optimal(data)
        if len(blob) > room:
            print("   rec%-4d SKIPPED: japanese needs %d, slot %d"
                  % (ri, len(blob), room))
            skipped += 1
            continue
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
        done += 1

    print("\n%d reverted, %d skipped" % (done, skipped))
    if write and done:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
