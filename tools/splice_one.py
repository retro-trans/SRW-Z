# -*- coding: utf-8 -*-
"""Splice a single record's freshly-built blob into an existing ISO's STAGE
region IN PLACE (other records untouched). Uses apply_record (with current
fixes). Usage: splice_one.py <iso> <N>"""
import sys, os
import apply_stage as A
import banlz

def main():
    iso = sys.argv[1]; n = int(sys.argv[2])
    exp = A.apply_record(n)
    stage = open(os.path.join(A.WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()
    recs = banlz.decompress_all(bytearray(stage))
    s1 = recs[n][0]; s2 = recs[n+1][0] if n+1 < len(recs) else len(stage)
    slot = s2 - s1
    blob = A.compress_cached(n, exp, slot)
    rt, _ = banlz.decompress_record(blob, 0); assert rt == exp
    if len(blob) > slot:
        print("OVERSIZE %d>%d - skipped" % (len(blob), slot)); return
    with open(iso, "r+b") as f:
        f.seek(A.STAGE_LBA * A.SECTOR + s1)
        f.write(blob + b"\x00" * (slot - len(blob)))
    print("spliced rec%03d (%d bytes) into %s at STAGE+0x%X" % (n, len(blob), os.path.basename(iso), s1))

if __name__ == "__main__":
    main()
