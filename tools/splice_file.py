# -*- coding: utf-8 -*-
"""Write a same-size file back into the ISO at a known LBA (no relocation, no
pointer edits). Verifies the size matches the original before writing.

Usage: splice_file.py <iso> <newfile> <lba> [origfile]
"""
import os, sys

SECTOR = 2048

def main():
    iso, newf, lba = sys.argv[1], sys.argv[2], int(sys.argv[3])
    orig = sys.argv[4] if len(sys.argv) > 4 else None
    blob = open(newf, "rb").read()
    if orig:
        osz = os.path.getsize(orig)
        assert len(blob) == osz, "size changed: %d != %d" % (len(blob), osz)
    with open(iso, "r+b") as f:
        f.seek(lba * SECTOR)
        f.write(blob)
        f.seek(lba * SECTOR)
        back = f.read(len(blob))
    print("spliced %s (%d bytes) at LBA %d -> verify %s"
          % (os.path.basename(newf), len(blob), lba, back == blob))

if __name__ == "__main__":
    main()
