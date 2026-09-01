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

Run against the image BEFORE building:

    verify_pointers.py <iso>                       # report only, never fails
    verify_pointers.py <iso> --against <ref-iso>   # STRONGEST, needs a good iso
    verify_pointers.py <iso> --min 85              # legacy, WARNS only

THE RATIO HAS A BLIND SPOT, and a flat threshold on it is not a gate.

Its denominator counts every 4-aligned word whose value happens to fall inside
the record, so it INFLATES when a record grows - and relocating a row (append +
repoint) grows the record legitimately. rec48 went 86.0% -> 84.9% across one
session with the numerator unchanged at 1087 and not one pointer broken.

`--min 85` was worse than useless. Measured 2026-08-31, TWENTY-SEVEN records of
the UNTOUCHED JAPANESE DISC score below 85%, rec48 among them at 84.4% - lower
than our own 84.9%. A user of the public 0.9.0 release ran this tool, got
"FAIL: 1 records below 85.0% - DO NOT BUILD" on a perfectly good image, and
reported it as a bug. The threshold was wrong, not the image. --min therefore
only WARNS now and never exits non-zero; lowering a threshold until it passes
is not a fix, so it was removed as a gate instead.

WHAT GATES INSTEAD, in order of strength:

  --against  takes every pointer that RESOLVES in a known-good image and
             requires it to still resolve. Size changes cannot affect it and a
             broken pointer cannot hide behind a big denominator. Use this
             whenever a known-good image is on hand - it is the real check.

  baseline   pointer_baseline.json holds the per-record scores of the untouched
             Japanese disc. It is printed beside our own for scale and DOES NOT
             GATE. Judging per-record against it was tried and is invalid for
             the same reason a flat --min is - an English record is thousands
             of bytes bigger, so the ratio sinks with nothing broken. It flagged
             rec72/34/82 as failures when each had MORE pointers landing than
             the Japanese disc did. Neither the ratio nor the raw count survives
             the crossing between two different images.
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


def against(cur_path, ref_path):
    """Every pointer that resolves in ref must still resolve in cur."""
    def load(p):
        f = open(p, "rb"); f.seek(LBA * SECTOR)
        it = banlz.decompress_all(f.read(SIZE)); f.close()
        return it

    cur, ref = load(cur_path), load(ref_path)
    broken = 0
    checked = 0
    for i in range(min(len(cur), len(ref))):
        a, b = ref[i][1], cur[i][1]
        if a is None or b is None:
            continue
        a, b = bytes(a), bytes(b)
        for p in range(0, min(len(a), len(b)) - 4, 4):
            v = struct.unpack_from("<I", a, p)[0] - BASE
            if not (0 <= v < len(a)) or (v and a[v - 1] != 0):
                continue
            # Require a NON-EMPTY target. A word pointing at a NUL "resolves" to
            # an empty string, and most such words are not pointers at all -
            # they are bytes inside TEXT that happen to read as an address. Any
            # edit to that text changes them, which would otherwise report
            # hundreds of phantom breakages.
            if v >= len(a) or a[v] == 0:
                continue
            # And require the target to look like a ROW - a dialogue row is
            # 'speaker' + newline + body. Single characters ('7', '+') are
            # text bytes that read as an address, not pointers; without this
            # they report as phantom breakages whenever the text is edited.
            end = a.find(bytes([0]), v)
            if end < 0 or end - v < 6 or 10 not in a[v:end]:
                continue
            checked += 1
            w = struct.unpack_from("<I", b, p)[0] - BASE
            if not (0 <= w < len(b)) or (w and b[w - 1] != 0):
                broken += 1
                if broken <= 8:
                    print("   rec%-4d word %#08x no longer resolves" % (i, p))
    print("pointers resolving in %s : %d" % (ref_path, checked))
    print("no longer resolving in %s : %d" % (cur_path, broken))
    return broken


def main():
    iso = sys.argv[1]
    if "--against" in sys.argv:
        ref = sys.argv[sys.argv.index("--against") + 1]
        sys.exit(1 if against(iso, ref) else 0)
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
            # Deliberately not fatal - see the header. The Japanese disc itself
            # has 27 records under 85%, so this number says nothing on its own.
            print("\nNOTE: %d record(s) below %.1f%%. This is NOT a failure - "
                  "the untouched" % (len(bad), floor))
            print("Japanese disc has 27 records below that itself. Use "
                  "--against for a real check.")
            for pc, idx, t, o in bad[:20]:
                print("   rec%-4d %.1f%%" % (idx, pc))
        else:
            print("\nEvery record is at or above %.1f%%." % floor)

    sys.exit(baseline_gate(worst))


def baseline_gate(worst):
    """Show each record beside the SAME record on the untouched Japanese disc.

    INFORMATIONAL ONLY - always returns 0. Comparing percentages across the
    two discs was tried as a gate on 2026-08-31 and is invalid for exactly the
    reason a flat --min is: an English record is thousands of bytes bigger than
    its Japanese original, so more coincidental words fall in range and the
    ratio sinks with nothing broken. Measured:

        rec72   japanese 652/652 100.0%   english 751/654 87.1%   ok +2
        rec34   japanese 719/719 100.0%   english 823/721 87.6%   ok +2
        rec82   japanese 716/716 100.0%   english 797/718 90.1%   ok +2

    Every one of those "failures" had MORE pointers landing correctly than the
    Japanese disc did. The numerator is not comparable either - it counts
    coincidental words too, and different text produces a different set of
    them. Neither half of the ratio survives the crossing, so this prints and
    does not judge. --against is the only real gate.
    """
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "pointer_baseline.json")
    if not os.path.exists(path):
        return 0
    base = json.load(open(path))["records"]
    rows = []
    for pc, idx, t, o in worst[:10]:
        ref = base.get(str(idx))
        if ref:
            rows.append((idx, o, t, pc, ref[1], ref[0], 100.0 * ref[1] / ref[0]))
    if rows:
        print("\nsame records on the UNTOUCHED JAPANESE DISC, for scale:")
        for idx, o, t, pc, ro, rt, rpc in rows:
            flag = "  <- we score HIGHER than the original" if pc > rpc else ""
            print("   rec%-4d this image %5d/%-5d %5.1f%%   japanese %5d/%-5d "
                  "%5.1f%%%s" % (idx, o, t, pc, ro, rt, rpc, flag))
    print("\nThis report is INFORMATIONAL and cannot fail a build - the ratio is "
          "not\ncomparable across images. For a real check run:")
    print("   verify_pointers.py <iso> --against <known-good iso>")
    return 0


if __name__ == "__main__":
    main()
