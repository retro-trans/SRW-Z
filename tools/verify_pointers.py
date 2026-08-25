# -*- coding: utf-8 -*-
"""Structural gate: every pointer must still land on the START of a string.

Written after v0.8.72 shipped corrupt. `fix_fullwidth.py` rebuilt each record
with `"\\x00".join(parts)` after shortening strings, which pulled everything
after each edit LEFT while the pointer table kept the old offsets. Record
LENGTH was unchanged (the tail was NUL-padded), so every length-based check
passed. The game booted, New Game played, and loading a save froze.

A pointer into a record should address the first byte of a NUL-terminated
string, i.e. the preceding byte is NUL. Measure the share that do; a content
edit must not move it. In a healthy record it is typically 100%; the corrupt
build dropped to ~26%.

Run against the image BEFORE building, and against a known-good image to get
the baseline:

    verify_pointers.py <iso>              # report
    verify_pointers.py <iso> --min 99     # exit 1 if any record falls below
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0


def score(data):
    """Return (pointers, landing_on_string_start)."""
    b = bytes(data)
    tot = ok = 0
    for p in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, p)[0] - BASE
        if not (0 <= v < len(b)):
            continue
        tot += 1
        if v == 0 or b[v - 1] == 0:
            ok += 1
    return tot, ok


def main():
    iso = sys.argv[1]
    floor = None
    if "--min" in sys.argv:
        floor = float(sys.argv[sys.argv.index("--min") + 1])
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()

    worst, tot_p, tot_ok = [], 0, 0
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        t, o = score(data)
        if not t:
            continue
        tot_p += t
        tot_ok += o
        worst.append((100.0 * o / t, idx, t, o))
    worst.sort()
    print("records scored : %d" % len(worst))
    print("pointers       : %d" % tot_p)
    print("land on a string start: %d  (%.2f%%)"
          % (tot_ok, 100.0 * tot_ok / max(1, tot_p)))
    print("\nworst 10 records:")
    for pc, idx, t, o in worst[:10]:
        print("   rec%-4d %6d pointers  %6d ok  %.1f%%" % (idx, t, o, pc))
    if floor is not None:
        bad = [w for w in worst if w[0] < floor]
        if bad:
            print("\nFAIL: %d records below %.1f%% - DO NOT BUILD" % (len(bad), floor))
            for pc, idx, t, o in bad[:20]:
                print("   rec%-4d %.1f%%" % (idx, pc))
            sys.exit(1)
        print("\nOK: every record at or above %.1f%%" % floor)


if __name__ == "__main__":
    main()
