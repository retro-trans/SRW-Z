# -*- coding: utf-8 -*-
"""Restore one file's sectors in an ISO from the original Japanese image.

Used to back out a patch that broke the game without rebuilding everything.
Resolves the file's CURRENT LBA from the game's own table (VMAP.DAT), so it
works for relocated files too.

Usage: restore_region.py <iso> <\\DATA\\NAME.BIN;1> [jp_image]
"""
import os
import struct
import sys

SEC = 2048
DEFAULT_JP = r"E:\Projects\SRW Z\_cmp\jp.bin"


def main():
    iso = sys.argv[1]
    name = sys.argv[2]
    jp = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_JP

    key = name.encode("ascii")
    f = open(iso, "rb")
    boot = f.read(0x120000)
    f.close()
    k = boot.find(key)
    if k < 0:
        raise SystemExit("not found in file table: %s" % name)
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    if not (0 < lba < 4000000 and 0 < nsec < 500000):
        raise SystemExit("implausible entry: LBA %d, %d sectors" % (lba, nsec))
    print("%s -> LBA %d, %d sectors" % (name, lba, nsec))

    g = open(jp, "rb")
    g.seek(lba * SEC)
    orig = g.read(nsec * SEC)
    g.close()

    o = open(iso, "r+b")
    o.seek(lba * SEC)
    o.write(orig)
    o.close()

    c = open(iso, "rb")
    c.seek(lba * SEC)
    ok = c.read(nsec * SEC) == orig
    c.close()
    print("restored from %s: %s" % (os.path.basename(jp), ok))


if __name__ == "__main__":
    main()
