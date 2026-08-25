# -*- coding: utf-8 -*-
"""Audit the game's own filename->LBA table for overlapping extents.

SRW Z loads data through this table, NOT the ISO9660 directory, so this is the
only view that can prove two relocated files do not collide. COMPDATA, the
MTVZKN encyclopedia files and SRVC all live in the DMY padding now.

Entry layout: the name `\\PATH\\NAME.EXT;1` starts a field, and
[u32 LBA][u32 size_in_sectors] sit at name+0x28 (NOT +0x20 - that reads zeros).
"""
import os
import re
import struct
import sys

ISO = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "iso", "srwz_fix3.bin")
FIELD = 0x28

f = open(ISO, "rb")
boot = f.read(0x120000)
size_sectors = os.path.getsize(ISO) // 2048
f.close()

pat = re.compile(rb"\\\\[A-Z0-9_]{1,12}\\\\[A-Z0-9_\.]{1,14};1")
ents = {}
for m in pat.finditer(boot):
    k = m.start()
    lba, nsec = struct.unpack_from("<II", boot, k + FIELD)
    if not (0 < lba < 4000000 and 0 < nsec < 500000):
        continue
    ents.setdefault(m.group().decode("ascii", "replace"), (lba, nsec))

rows = sorted(ents.items(), key=lambda kv: kv[1][0])
print("%-26s %10s %8s %10s" % ("file", "LBA", "sectors", "end"))
for nm, (lba, nsec) in rows:
    print("%-26s %10d %8d %10d" % (nm[:26], lba, nsec, lba + nsec))

print("\n--- overlap check (DMY is expected to contain the relocated files) ---")
clash = 0
for i in range(len(rows)):
    ni, (li, si) = rows[i]
    for j in range(i + 1, len(rows)):
        nj, (lj, sj) = rows[j]
        if lj >= li + si:
            break
        if "DMY" in ni or "DMY" in nj:
            continue                       # padding host, by design
        print("  COLLISION: %s [%d..%d] vs %s [%d..%d]"
              % (ni, li, li + si, nj, lj, lj + sj))
        clash += 1
print("  real collisions: %d" % clash)

past = [(n, l, s) for n, (l, s) in rows if l + s > size_sectors]
print("\nentries past end of image (%d sectors): %d" % (size_sectors, len(past)))
for n, l, s in past:
    print("   %s ends at %d" % (n, l + s))
