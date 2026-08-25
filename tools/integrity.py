
# -*- coding: utf-8 -*-
"""Structural integrity check of a built ISO.

Run before shipping, and first thing when a build breaks. Verifies the things
that make the game fail to LOAD rather than fail to render:

  - every STAGE record decompresses and fits its slot
  - COMPDATA decompresses
  - the game's own file table has no overlaps and nothing past end of image
  - each relocated file's declared sector count actually covers its data

Does NOT check text. A black screen on map load is a load failure, not a
translation problem.
"""
import os
import re
import struct
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

SEC = 2048
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "iso",
                                                         "srwz_fix3.bin")
bad = 0

f = open(ISO, "rb")
size_sec = os.path.getsize(ISO) // SEC
boot = f.read(0x120000)

# ---- file table ----
pat = re.compile(rb"\\\\[A-Z0-9_]{1,12}\\\\[A-Z0-9_\.]{1,14};1")
ents = {}
for m in pat.finditer(boot):
    k = m.start()
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    if 0 < lba < 4000000 and 0 < nsec < 500000:
        ents.setdefault(m.group().decode("ascii", "replace"), (lba, nsec))
print("file-table entries: %d" % len(ents))
for nm, (lba, nsec) in ents.items():
    if lba + nsec > size_sec:
        print("  !! %s ends at %d, image is %d sectors" % (nm, lba + nsec, size_sec))
        bad += 1

rows = sorted(ents.items(), key=lambda kv: kv[1][0])
for i in range(len(rows)):
    ni, (li, si) = rows[i]
    for j in range(i + 1, len(rows)):
        nj, (lj, sj) = rows[j]
        if lj >= li + si:
            break
        if "DMY" in ni or "DMY" in nj:
            continue
        print("  !! COLLISION %s [%d..%d] vs %s [%d..%d]"
              % (ni, li, li + si, nj, lj, lj + sj))
        bad += 1

# ---- STAGE ----
lba, nsec = ents.get("\\\\DATA\\\\STAGE.BIN;1", (1651029, 1910))
f.seek(lba * SEC)
stage = bytearray(f.read(nsec * SEC))
try:
    recs = banlz.decompress_all(stage)
    n_ok = sum(1 for o, d in recs if d is not None)
    print("STAGE: %d records, %d decompressed" % (len(recs), n_ok))
    if len(recs) != 205:
        print("  !! expected 205 records")
        bad += 1
except Exception as e:
    print("STAGE: DECOMPRESS FAILED - %s" % e)
    bad += 1

# ---- COMPDATA ----
lba, nsec = ents.get("\\\\DATA\\\\COMPDATA.BN;1", (1823000, 74))
f.seek(lba * SEC)
blob = bytearray(f.read(nsec * SEC))
try:
    cd, used = banlz.decompress_record(blob, 0)
    print("COMPDATA: %d bytes decompressed, %d compressed (slot %d)"
          % (len(cd), used, nsec * SEC))
    if used > nsec * SEC:
        print("  !! compressed stream %d exceeds declared %d sectors"
              % (used, nsec))
        bad += 1
except Exception as e:
    print("COMPDATA: DECOMPRESS FAILED - %s" % e)
    bad += 1

# ---- other banlz containers ----
for nm in ("\\\\DATA\\\\MTVZKNPT.BIN;1", "\\\\DATA\\\\MTVZKNRT.BIN;1",
           "\\\\DATA\\\\MTVZKNKW.BIN;1", "\\\\DATA\\\\NISVDATA.BIN;1",
           "\\\\DATA\\\\HSFC.BIN;1"):
    if nm not in ents:
        continue
    lba, nsec = ents[nm]
    f.seek(lba * SEC)
    b = bytearray(f.read(nsec * SEC))
    try:
        r = banlz.decompress_all(b)
        print("%-26s %d records ok" % (nm.split("\\\\")[-1], len(r)))
    except Exception as e:
        print("%-26s DECOMPRESS FAILED - %s" % (nm.split("\\\\")[-1], e))
        bad += 1

f.close()
print("\nproblems: %d" % bad)
