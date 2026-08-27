# -*- coding: utf-8 -*-
"""Reproduce the discovery of how COMPDATA name references are stored.

Run it against a 32MB EE RAM dump (PCSX2 -> tools/pine_dump.py) plus the
COMPDATA record. It re-derives, from scratch:

  * the hardcoded load address of the record (0x006D6800)
  * that the references are ABSOLUTE PS2 ADDRESSES, not indices or offsets
  * where the pointer tables and the string pool live
  * that nothing outside COMPDATA points into the pool

Kept because the negative result is the interesting part: every static search of
the 3.7GB image failed - index, record-relative offset, offset/8, and the target
unit's six-weapon sequence at every stride from 2 to 128 - because the stored
value is an absolute 0x0073xxxx that resembles nothing on disc. Searching a RAM
dump answered it in minutes. When a reference cannot be found statically, dump
RAM before concluding it is computed at runtime.

Usage: find_pool_pointers.py <ee_dump.bin> [compdata_record.bin]
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool

ANCHOR = b"Rust Hurricane"      # english build; JP anchor is 0x66400
ANCHOR_OFF = 0x66400


def main():
    dump = sys.argv[1]
    recsrc = sys.argv[2] if len(sys.argv) > 2 else "extracted/DATA_COMPDATA.BN"
    ram = open(dump, "rb").read()
    raw = open(recsrc, "rb").read()
    rec = bytes(banlz.decompress_all(raw)[0][1])
    print("record: %d bytes from %s" % (len(rec), recsrc))

    a = ram.find(ANCHOR)
    if a < 0:
        raise SystemExit("anchor %r not in the dump - is it an english build?"
                         % ANCHOR)
    base = a - ANCHOR_OFF
    print("anchor %r at ram %#x -> load address %#010x" % (ANCHOR, a, base))
    if base != pool.BASE:
        print("WARNING: differs from pool.BASE %#010x" % pool.BASE)

    same = ram[base + 0x35800:base + 0x35870] == rec[0x35800:0x35870]
    print("pointer-table bytes identical in file and RAM: %s "
          "(so nothing is relocated at load)" % same)

    ent = pool.entries(rec)
    starts = set(x[0] for x in ent)
    ptrs = pool.pointers(rec, starts)
    print("pool  %#x..%#x: %d entries, all 8-aligned: %s"
          % (pool.POOL_LO, pool.POOL_HI, len(ent),
             all(o % 8 == 0 for o, _, _ in ent)))
    print("pointer words: %d, spanning %#x..%#x"
          % (len(ptrs), ptrs[0][0], ptrs[-1][0]))
    print("pool strings with no pointer: %d" % len(starts - set(t for _, t in ptrs)))

    gaps = collections.Counter(b[0] - a[0] for a, b in zip(ptrs, ptrs[1:]))
    print("pointer-word gap histogram: %s" % gaps.most_common(5))

    # references from outside the loaded record. Most are transient heap copies
    # and repopulate from the table; only a reference in the ELF's own static
    # data would survive a rebuild and need patching, so those are cross-checked
    # against the ELF ON DISC rather than assumed away.
    ext = []
    for p in range(0, len(ram) - 4, 4):
        v = struct.unpack_from("<I", ram, p)[0]
        if base <= v < base + len(rec) and (v - base) in starts:
            if not (base <= p < base + len(rec)):
                ext.append((p, v - base))
    zones = collections.Counter()
    for p, t in ext:
        zones["ELF static window" if 0x100000 <= p < 0x600000 else "heap"] += 1
    print("references from OUTSIDE the record: %d %s" % (len(ext), dict(zones)))

    elfpath = "extracted/SLPS_258.87"
    if os.path.exists(elfpath):
        elf = open(elfpath, "rb").read()
        VBASE, FOFF = 0x100000, 0x1A80
        real = 0
        for p, t in ext:
            if not (0x100000 <= p < 0x600000):
                continue
            fo = p - VBASE + FOFF
            if 0 <= fo < len(elf) - 4 and struct.unpack_from("<I", elf, fo)[0] == base + t:
                print("   candidate in ELF at ram %#010x -> rec %#08x" % (p, t))
                print("     context %s"
                      % " ".join("%02x" % b for b in elf[fo - 4:fo + 8]))
                real += 1
        print("candidates present in the shipped ELF: %d" % real)
        print("  (inspect the context: a run of u16 values whose high half is "
              "0x0074 reads as a pool address by accident, e.g. `00 a2 74 00`. "
              "Every candidate found so far has been one of those, so the pool "
              "has NO static references outside COMPDATA and can be repacked.)")

    st = pool.strays(rec, starts)
    print("pointer-SHAPED words that miss a string start: %d" % len(st))
    print("  every one inspected was a u16 pair with high half 0x0074 "
          "(bytes like `00 a2 74 00`) - not a pointer, never rewritten")


if __name__ == "__main__":
    main()
