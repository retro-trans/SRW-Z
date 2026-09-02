# -*- coding: utf-8 -*-
"""Update each STAGE record's END-OF-RECORD marker after the record grew.

REPORTED: the game crashes immediately after Ziene's line at the end of the
Emaan scene. Bisected by the user, one variable at a time, to STAGE -> rec79 ->
row 157, a single line of Gain's dialogue. Moving that line elsewhere - same
bytes - fixed it, so the fault was its ADDRESS, not its text.

THE HEADER. Every STAGE record begins with a header. Word 0x28 (and 0x2c)
holds BASE + the record's own length: a pointer one past the last byte, the
record's declared end. It holds exactly that in 205 of 205 japanese records, so
it is an invariant, not a coincidence.

    rec79 japanese: length 0x7410, word 0x28 = BASE+0x7410
    rec79 ours    : length 0x74f2, word 0x28 = BASE+0x7410   <- STALE

WHAT WENT WRONG. Successive passes appended relocated strings to the tail of a
record, starting at the old end, and never updated the marker. So the first
appended string begins at exactly the address the header still calls the end.
rec79's row 157 is such a string, 63 bytes long, and reading it runs the game
past its own declared bounds.

That is why the placeholder test passed and the full line failed at the same
address: a 9-byte stand-in stops just past the boundary, a 63-byte line does
not. And it is why 161 records are exposed - every record that grew.

THE FIX. Set the marker to the record's real length, restoring the invariant.
Only words that held the japanese length are touched, so a record whose header
means something else is left alone. No text moves and no pointer changes.

Usage: fix_record_end_marker.py <iso> [--write] [--check]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
WORDS = (0x28, 0x2C)
JP_ISO = "iso/srwz.bin"


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    check = "--check" in sys.argv

    jp = [(h, d) for h, d in banlz.decompress_all(load(JP_ISO))
          if isinstance(h, int) and d is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    stale = []
    for ri in range(min(len(live), len(jp))):
        jb = bytes(jp[ri][1])
        eb = bytes(live[ri][1])
        if len(jb) < 0x30 or len(eb) < 0x30:
            continue
        for w in WORDS:
            jv = struct.unpack_from("<I", jb, w)[0] - BASE
            ev = struct.unpack_from("<I", eb, w)[0] - BASE
            if jv != len(jb):
                continue                      # not an end marker in this record
            if ev != len(eb):
                stale.append((ri, w, ev, len(eb)))

    if check:
        print("stale end-of-record markers: %d" % len(stale))
        if not stale:
            print("end-marker gate OK: every record declares its real length")
            return 0
        for ri, w, have, want in stale[:12]:
            print("   rec%-4d word %#04x says %#07x, record is %#07x"
                  % (ri, w, have, want))
        return 1

    print("stale end-of-record markers: %d" % len(stale))
    by_rec = {}
    for ri, w, have, want in stale:
        by_rec.setdefault(ri, []).append(w)

    done = 0
    for ri, words in sorted(by_rec.items()):
        hdr = live[ri][0]
        d = bytearray(live[ri][1])
        for w in words:
            struct.pack_into("<I", d, w, BASE + len(d))
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        if len(blob) > nxt - hdr:
            print("   rec%-4d SKIPPED: %d bytes, slot %d" % (ri, len(blob), nxt - hdr))
            continue
        if write:
            raw[hdr:hdr + len(blob)] = blob
            for x in range(hdr + len(blob), nxt):
                raw[x] = 0
        done += 1
        if done <= 8:
            print("   rec%-4d marker -> %#07x  (%d word(s))" % (ri, len(d), len(words)))

    print("\n%d record(s) corrected" % done)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
