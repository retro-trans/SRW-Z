# -*- coding: utf-8 -*-
"""Apply EQUAL-LENGTH spelling corrections inside a compressed bank.

Only same-byte-length pairs are allowed, so nothing in the record moves - the
safest possible edit for a bank that other tables may index by offset (the
lesson SRVC taught us). Records are decompressed from the CURRENT iso, edited,
recompressed with the optimal packer, and spliced back into their own slots;
every untouched record is verified byte-identical afterwards.

Usage: patch_spelling.py <iso> <bank> [--dry-run]
   bank: STAGE
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz

SECTOR = 2048
BANKS = {"STAGE": (1651029, 3910128)}

# (wrong, right) - MUST be the same length
PAIRS = [
    (b"Chilam", b"Chiram"),      # the game's own UI and pilot data say Chiram
]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path, bank = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    for a, b in PAIRS:
        assert len(a) == len(b), "%r/%r differ in length" % (a, b)
    lba, size = BANKS[bank]
    f = open(iso_path, "r+b")
    f.seek(lba * SECTOR)
    raw = bytearray(f.read(size))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, hits = {}, 0
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        d = bytes(dec)
        n = sum(d.count(a) for a, _ in PAIRS)
        if not n:
            continue
        for a, b in PAIRS:
            d = d.replace(a, b)
        edited[idx] = (hdr, d)
        hits += n
    print("%s: %d records hold %d occurrence(s)" % (bank, len(edited), hits))
    if dry or not edited:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    packed = dict(pool.map(_compress, [(i, d) for i, (h, d) in edited.items()]))
    pool.close(); pool.join()

    for idx, (hdr, plain) in edited.items():
        blob = packed[idx]
        end = hdr
        while end < len(raw) and raw[end] == 0:
            end += 1
        # slot = up to the next record header (or the zero padding after it)
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "record %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = 0
    for o in before:
        if check[o] != before[o]:
            changed += 1
    assert changed == len(edited), "unexpected records changed (%d)" % changed
    f.seek(lba * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % changed)


if __name__ == "__main__":
    main()
