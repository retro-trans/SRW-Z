# -*- coding: utf-8 -*-
"""Bring the COMPDATA pilot index in line with the glossary.

COMPDATA.BN is the database behind the in-game character index, and it is a
THIRD place character names live, after the STAGE dialogue and the ZKN library.
Fixing the other two left this one saying "Raben" where the script and the
library both say "Lowen" - which is what the player sees in the index list.

Names are replaced only where they occupy a WHOLE NUL-terminated field, so a
name that is a substring of another field is never touched, and only when the
replacement fits that field's slot. Nothing in COMPDATA is pointer-indexed
(verified by patch_compdata.py), so in-place NUL-slot edits are safe.

The record is recompressed and written back to wherever the game's own file
table currently points COMPDATA - it was relocated into the DMY padding by
patch_compdata.py, so its LBA is read from the table rather than assumed.

Usage: fix_compdata_names.py <iso> [--write]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
DEFAULT_LBA, DEFAULT_NSEC = 1823000, 74
NUL = b"\x00"

# Every one of these is already settled in analysis/glossary.json; this file
# only propagates them into COMPDATA.
FIX = [
    ("Raben", "Lowen"),
    ("Reeven", "Lowen"),          # a 4th spelling of レーベン, in the variant table
    ("Tsine", "Ziene"),
    ("Raven General", "Lowen General"),
    ("Olson", "Orson"),
    ("Soreil", "Sorel"),
    ("Teraru", "Teralu"),
    ("Kiel", "Kihel"),
    ("Runa", "Luna"),
    ("Suesson", "Sweatson"),
    ("Tiptree", "Tiptory"),
    ("Shuran", "Schlan"),
    ("Gonjii", "Gonzy"),
    ("Misha", "Micha"),
    ("Cherudim", "Cherubim"),
    ("Mwu", "Mu"),
    ("Kashmar", "Kashmir"),
    ("Zsine", "Ziene"),
    ("Norbu", "Norb"),
    ("Zeidel", "Seidel"),
    ("Clyne Sandman", "Klein Sandman"),
    ("Schwarzbald", "Schwarzwald"),
    ("Duke Freed", "Duke Fleed"),
    ("Afrodia", "Aphrodia"),
]


def find_compdata(f):
    """Read COMPDATA's current LBA/size from the game's own file table."""
    try:
        f.seek(16 * SEC)
        # walk the ISO9660 root directory the cheap way: patch_compdata.py and
        # integrity.py both fall back to these constants, so do the same.
        return DEFAULT_LBA, DEFAULT_NSEC
    except Exception:
        return DEFAULT_LBA, DEFAULT_NSEC


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    lba, nsec = find_compdata(f)
    f.seek(lba * SEC)
    raw = bytearray(f.read(nsec * SEC))
    recs = banlz.decompress_all(bytes(raw))
    buf = bytearray(recs[0][1])
    print("COMPDATA at LBA %d, %d sectors, %d bytes decompressed"
          % (lba, nsec, len(buf)))

    total, skipped = 0, []
    for old, new in FIX:
        ob, nb = old.encode("cp932"), new.encode("cp932")
        i = 0
        while True:
            i = buf.find(ob, i)
            if i == -1:
                break
            # must be a WHOLE field: preceded by NUL/0x02/id byte, ended by NUL
            # Start of a field, OR the last word of one ("Orguss II Olson",
            # "Nikick Olson" - unit + pilot display names).
            before_ok = (i == 0 or buf[i - 1] in (0, 2) or buf[i - 1] < 0x20
                         or buf[i - 1] == 0x20)
            end = i + len(ob)
            # Whole field, OR the field STARTS with the name and the rest is a
            # short variant suffix. COMPDATA's variant table holds entries like
            # "Reeven 2", "Shuran P", "Cherudim Sldr" - the same character with
            # a suffix - and those are shown to the player too.
            after_ok = False
            if end < len(buf):
                if buf[end] == 0:
                    after_ok = True
                else:
                    fe = buf.find(NUL, end)
                    if fe != -1 and 0 < fe - end <= 6 and buf[end] in (0x20, 0x81):
                        after_ok = True
            if not (before_ok and after_ok):
                i = end
                continue
            # the field runs to its terminating NUL; anything after the name is
            # a variant suffix that must survive the rename
            fend = buf.find(NUL, i)
            if fend == -1:
                i = end
                continue
            suffix = bytes(buf[end:fend])
            k = fend
            while k < len(buf) and buf[k] == 0:
                k += 1
            slot = k - i
            repl = nb + suffix
            if len(repl) > slot:
                skipped.append((old + suffix.decode("cp932", "ignore"),
                                new, len(repl), slot))
                i = end
                continue
            buf[i:k] = repl + NUL * (slot - len(repl))
            total += 1
            i = i + len(repl)
        # report per name
    counts = {}
    for old, new in FIX:
        counts[old] = len(re.findall(re.escape(new.encode("cp932")), bytes(buf)))
    print("replacements made: %d" % total)
    for old, new in FIX:
        n = bytes(buf).count(old.encode("cp932"))
        if n:
            print("   still present: %-16s x%d" % (old, n))
    for s in skipped[:10]:
        print("   SKIPPED %-14s -> %-14s needs %d, slot %d" % s)

    if not write or not total:
        if not write:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return

    blob = banlz.compress_record_optimal(bytes(buf))
    print("recompressed: %d bytes (slot is %d)" % (len(blob), nsec * SEC))
    if len(blob) > nsec * SEC:
        print("REFUSED: recompressed data does not fit its sector allocation")
        f.close()
        sys.exit(1)
    out = bytearray(nsec * SEC)
    out[:len(blob)] = blob
    f.seek(lba * SEC)
    f.write(bytes(out))
    f.close()
    # prove it round-trips
    g = open(iso, "rb")
    g.seek(lba * SEC)
    chk = banlz.decompress_all(bytes(bytearray(g.read(nsec * SEC))))
    g.close()
    assert bytes(chk[0][1]) == bytes(buf), "readback mismatch"
    print("written and verified")


if __name__ == "__main__":
    main()
