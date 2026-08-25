# -*- coding: utf-8 -*-
"""Diff two 3.5GB PS2 disc images at sector granularity, report changed LBA
ranges, and label each with the file it belongs to via the game's internal
file table (\\DATA\\NAME... [u32 LBA][u32 sectors] at name+0x20)."""
import struct, sys

SECTOR = 2048
A = r"E:\Projects\SRW Z\_work\iso\srwz.bin"                  # pristine
B = sys.argv[1] if len(sys.argv) > 1 else r"E:\Projects\SRW Z\_work\iso\srwz_DIAG_origelf.bin"

# build LBA->file map from internal file table in first 4MB of pristine
head = open(A, "rb").read(6 * 1024 * 1024)
files = []  # (lba, sectors, name)
i = head.find(b"\\")
# scan for entries like \XXX\NAME;1 with a 4-byte-aligned [lba][sectors] at +0x20
import re
for m in re.finditer(rb"\\[A-Z0-9_]+\\[A-Z0-9_.]+;1", head):
    nm = m.group(0)
    pos = m.end()  # name may be padded; table lba is at name_start+0x20 per patch_compdata
    st = m.start()
    lba = struct.unpack_from("<I", head, st + 0x20)[0]
    sec = struct.unpack_from("<I", head, st + 0x24)[0]
    if 0 < lba < 2_000_000 and 0 < sec < 2_000_000:
        files.append((lba, sec, nm.decode("latin1")))
files.sort()

def label(lba):
    best = None
    for l, s, nm in files:
        if l <= lba < l + s:
            return nm
        if l <= lba:
            best = nm
    return "?(after %s)" % best if best else "?"

fa = open(A, "rb"); fb = open(B, "rb")
CH = 4 * 1024 * 1024
off = 0
changed = []  # (start_lba, end_lba)
cur = None
while True:
    da = fa.read(CH); db = fb.read(CH)
    if not da or not db:
        break
    if da != db:
        # find differing sectors within this chunk
        n = min(len(da), len(db))
        for s in range(0, n, SECTOR):
            if da[s:s+SECTOR] != db[s:s+SECTOR]:
                lba = (off + s) // SECTOR
                if cur and lba == cur[1] + 1:
                    cur = (cur[0], lba)
                else:
                    if cur: changed.append(cur)
                    cur = (lba, lba)
    off += len(da)
if cur: changed.append(cur)
fa.close(); fb.close()

print("changed LBA ranges: %d\n" % len(changed))
print("%-10s %-10s %-8s %s" % ("startLBA", "endLBA", "sectors", "file"))
from collections import defaultdict
bytot = defaultdict(int)
for a, b in changed:
    nsec = b - a + 1
    lbl = label(a)
    bytot[lbl] += nsec
    print("%-10d %-10d %-8d %s" % (a, b, nsec, lbl))
print("\n=== sectors changed per file ===")
for lbl, n in sorted(bytot.items(), key=lambda x: -x[1]):
    print("  %-28s %d sectors (%.1f KB)" % (lbl, n, n * SECTOR / 1024))
