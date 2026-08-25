"""Write patched files back into the ISO at their original LBAs.

Only same-size replacements are allowed. That keeps every LBA and the whole
ISO9660 structure untouched, so no filesystem rebuild is needed and the
directory records stay valid.
"""
import sys
import os
import shutil

SECTOR = 2048

# (iso_path, lba, patched_file)
INJECT = [
    ("/SLPS_258.87",      455,     "SLPS_258.87"),
    ("/MAP/MAPNAME.BIN",  1652939, "MAP_MAPNAME.BIN"),
    ("/DATA/STAGE.BIN",   1651029, "DATA_STAGE.BIN"),
]

src_iso, dst_iso, patched_dir = sys.argv[1], sys.argv[2], sys.argv[3]

if not os.path.exists(dst_iso):
    print("copying ISO (%.2f GB)..." % (os.path.getsize(src_iso) / 1e9))
    shutil.copyfile(src_iso, dst_iso)
    print("  copy done")
else:
    print("reusing existing %s" % os.path.basename(dst_iso))

with open(dst_iso, "r+b") as iso:
    for iso_path, lba, fname in INJECT:
        p = os.path.join(patched_dir, fname)
        if not os.path.exists(p):
            print("  MISSING %s -- skipped" % fname)
            continue
        new = open(p, "rb").read()
        off = lba * SECTOR
        iso.seek(off)
        old = iso.read(len(new))
        if len(old) != len(new):
            print("  SIZE MISMATCH for %s -- refusing" % iso_path)
            continue
        iso.seek(off)
        iso.write(new)
        changed = sum(1 for a, b in zip(old, new) if a != b)
        print("  %-22s LBA %-9d %s bytes written, %s differ"
              % (iso_path, lba, "{:,}".format(len(new)), "{:,}".format(changed)))

print("\npatched ISO: %s (%.2f GB)" % (dst_iso, os.path.getsize(dst_iso) / 1e9))
