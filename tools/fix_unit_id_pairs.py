# -*- coding: utf-8 -*-
"""Restore 5 unit-table ID pairs that 0.8.90 overwrote with string pointers.

REPORTED: the Methuss unit screen draws a Nemo. Stats, name and parts are all
correct - only the mech drawn is wrong.

BISECTED by the user: 0.8.89 clean, 0.8.90 broken. 0.8.90's only change to the
disc is COMPDATA, and its only content change is tools/fix_pool_strays.py.

WHAT 0.8.90 DID. 0.8.81 repacked the COMPDATA string pool and rewrote every
word that looked like a pool pointer, deliberately skipping 91 that did not
land on a string start, on the reasoning that they were u16 pairs. 0.8.90
decided that reasoning was wrong for the 60 sitting on a pointer-table stride
and repaired 62 words.

For 57 of them that was right. For 5 it was not: they really are u16 ID PAIRS,
and the stride test cannot tell the difference because a unit record's first
word is at a stride by construction.

    @0x050d44  (0x00d1, 0x0074)   next 0x00fa
    @0x050d88  (0x00d1, 0x0075)   next 0x00fb
    @0x050dcc  (0x00d2, 0x0074)   next 0x00fc
    @0x050e10  (0x00d3, 0x0074)   next 0x00fd
    @0x050e54  (0x00d3, 0x0075)   next 0x00fe

WHY THEY LOOK LIKE POINTERS. The pool occupies RAM 0x0073E080..0x00756700, so
a pair whose HIGH half is 0x0073/0x0074/0x0075 reads as an address inside it by
pure coincidence. The proof is the record immediately above: 0x050d00 holds
(0x00d0, 0x0073), which resolves BELOW the pool start, so it was left alone -
while (0x00d1, 0x0074) resolved inside and was overwritten.

WHY THE MECH CHANGES. The unit table runs on a 0x44 stride:

    +0x00  u16 id, u16 id      <- this pair
    +0x04  u16 index           <- 0xf9, 0xfa, 0xfb ... sequential
    +0x08  name pointer
    +0x0c  HP ...

Methuss owns three records (name pointer at 0x050d08, 0x050d90, 0x050dd4). Two
of them had their leading pair clobbered, so the record still carries the right
name and the right stats - which is exactly what the screenshot shows - and
picks its artwork from a corrupted id.

THE FIX. Restore all five words from the pristine japanese disc. They were
never translated and never legitimately repointed, so the original value is
correct by definition.

Usage: fix_unit_id_pairs.py <iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
BASE = 0x006D6800                          # COMPDATA's load address in RAM
OURS_LBA, OURS_ROOM = 1823000, 409600     # COMPDATA relocated into DMY.BIN
JP_ISO, JP_LBA, JP_SIZE = "iso/srwz.bin", 1568198, 144990

SITES = [0x050d44, 0x050d88, 0x050dcc, 0x050e10, 0x050e54]


def record(path, lba, size):
    f = open(path, "rb")
    f.seek(lba * SEC)
    raw = f.read(size)
    f.close()
    items = [(h, d) for h, d in banlz.decompress_all(raw)
             if isinstance(h, int) and d is not None]
    if not items:
        raise SystemExit("no banlz record at LBA %d of %s" % (lba, path))
    return items[0]


def scan(jp, ours):
    """Every word with the id-pair signature, and whether ours still matches.

    The discriminator is the TARGET, not the stride: a real pointer lands on a
    string START, an id pair lands mid-string, because its value is not an
    address at all. That is the test 0.8.90 needed and did not have.
    """
    out = []
    n = min(len(jp), len(ours))
    for p in range(0, n - 8, 4):
        vj = struct.unpack_from("<I", jp, p)[0]
        lo, hi = vj & 0xFFFF, (vj >> 16) & 0xFFFF
        if hi not in (0x0073, 0x0074, 0x0075) or lo >= 0x0800:
            continue
        o = vj - BASE
        if not (0 <= o < len(jp)) or o == 0 or jp[o - 1] == 0:
            continue                      # lands on a string start -> a pointer
        vo = struct.unpack_from("<I", ours, p)[0]
        out.append((p, vj, vo))
    return out


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    check = "--check" in sys.argv

    _jh, jp = record(JP_ISO, JP_LBA, JP_SIZE)
    if check:
        _h, cur = record(iso, OURS_LBA, OURS_ROOM)
        rows = scan(bytes(jp), bytes(cur))
        bad = [(p, a, b) for p, a, b in rows if a != b]
        print("unit-table id pairs checked: %d" % len(rows))
        if not bad:
            print("id-pair gate OK: none overwritten by a pool repoint")
            return 0
        print("REGRESSION: %d id pair(s) hold a string pointer" % len(bad))
        for p, a, b in bad:
            print("   @%#08x  should be %#010x, is %#010x" % (p, a, b))
        return 1
    hdr, cur = record(iso, OURS_LBA, OURS_ROOM)
    jp, d = bytes(jp), bytearray(cur)
    if len(d) != len(jp):
        raise SystemExit("record length differs: ours %d, japanese %d"
                         % (len(d), len(jp)))

    fixed = 0
    for off in SITES:
        want = struct.unpack_from("<I", jp, off)[0]
        have = struct.unpack_from("<I", d, off)[0]
        lo, hi = want & 0xFFFF, (want >> 16) & 0xFFFF
        nxt = struct.unpack_from("<I", jp, off + 4)[0]
        # refuse to touch anything that is not the shape we diagnosed
        assert hi in (0x0073, 0x0074, 0x0075) and lo < 0x0800 and nxt < 0x10000, \
            "%#x is not a unit-table id pair" % off
        if have == want:
            print("   @%#08x already correct (%#010x)" % (off, want))
            continue
        print("   @%#08x  %#010x -> %#010x   id pair (%#06x, %#06x)"
              % (off, have, want, lo, hi))
        struct.pack_into("<I", d, off, want)
        fixed += 1

    print("\n%d word(s) restored" % fixed)
    if not fixed:
        return 0
    if not write:
        print("(dry run - pass --write to apply)")
        return 0

    blob = banlz.compress_record(bytes(d))
    if len(blob) > OURS_ROOM:
        blob = banlz.compress_record_optimal(bytes(d))
    if len(blob) > OURS_ROOM:
        raise SystemExit("recompressed COMPDATA does not fit: %d > %d"
                         % (len(blob), OURS_ROOM))
    f = open(iso, "r+b")
    f.seek(OURS_LBA * SEC)
    f.write(blob + b"\x00" * (OURS_ROOM - len(blob)))
    f.close()
    # read it straight back and confirm
    _h, back = record(iso, OURS_LBA, OURS_ROOM)
    for off in SITES:
        assert struct.unpack_from("<I", bytes(back), off)[0] == \
               struct.unpack_from("<I", jp, off)[0], "%#x did not stick" % off
    print("COMPDATA written (%d bytes) and verified" % len(blob))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
