# -*- coding: utf-8 -*-
"""Restore the ORIGINAL Japanese encyclopedia archives in an ISO.

A bisect tool. The encyclopedia crashes the game when backing out of a
character entry, and two guesses at the cause (an over-broad COMPDATA pass,
then record line counts) were both wrong. This puts the untouched Japanese
archives back - original bytes, original LBAs, original file-table entries and
original ELF offset tables - while leaving every other translation in place.

If the crash survives that, the encyclopedia data is not the cause and the
search moves elsewhere. If it stops, the cause is in our records and can be
narrowed further (byte size vs line count vs menu encoding).

With --reloc the ORIGINAL Japanese archives are written at the RELOCATED DMY
addresses instead of their own, which separates two variables that changed
together: our records are both bigger AND living somewhere else. If Japanese
data at the new location crashes, the fault is the relocation/size, not the
text we put in the records.

Usage: zkn_revert.py <iso> <in.elf> <out.elf> [--reloc]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from zkn_build import SETS, SECTOR, WORK, orig_offsets, RELOC


def main():
    iso_path, elf_in, elf_out = sys.argv[1], sys.argv[2], sys.argv[3]
    reloc = "--reloc" in sys.argv
    data = bytearray(open(elf_in, "rb").read())
    with open(iso_path, "r+b") as iso:
        for key, (fn, tab, n, ftent, olba, ocap) in SETS.items():
            blob = open(os.path.join(WORK, "extracted", fn), "rb").read()
            lba = RELOC[key] if reloc else olba
            sec = (len(blob) + SECTOR - 1) // SECTOR if reloc else ocap
            iso.seek(lba * SECTOR)
            iso.write(blob + b"\x00" * (sec * SECTOR - len(blob)))
            # point the game's file table at wherever we put it
            iso.seek(ftent + 0x28)
            iso.write(struct.pack("<II", lba, sec))
            print("%s: restored %d bytes at LBA %d (%d sectors)%s"
                  % (key, len(blob), lba, sec, "  [RELOCATED]" if reloc else ""))
            # and restore the ELF offset table (N entries + size sentinel)
            offs = orig_offsets(key) + [len(blob)]
            assert len(offs) == n + 1, "%s: %d offsets, expected %d" % (
                key, len(offs), n + 1)
            probe_now = struct.unpack_from("<3I", data, 0)  # placeholder
            # locate the table the same way zkn_build does
            found = -1
            for cand in (offs[1:4],):
                pr = struct.pack("<3I", *cand)
                found = data.find(pr)
                if found > 0:
                    break
            if found <= 0:
                # table currently holds OUR offsets; find it by its known address
                found = tab + 4
            base = found - 4
            data[base:base + 4 * (n + 1)] = struct.pack("<%dI" % (n + 1), *offs)
            print("   ELF table @0x%X restored (%d entries)" % (base, n + 1))
    open(elf_out, "wb").write(bytes(data))
    print("ELF written: %s" % elf_out)


if __name__ == "__main__":
    main()
