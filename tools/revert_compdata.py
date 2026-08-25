# -*- coding: utf-8 -*-
"""Revert patch_compdata's relocation: repoint COMPDATA.BN's ISO9660 dir record
and the game's internal file table back to the ORIGINAL LBA/size. The original
JP COMPDATA is still intact at ORIG_LBA (relocation never overwrote it), so this
is a pointer-only revert - the game loads the original, correctly-sized file.

Usage: revert_compdata.py <iso>
"""
import struct, sys

SECTOR = 2048
ORIG_LBA, ORIG_SIZE = 1568198, 144990
NEW_LBA = 1823000
ORIG_SECTORS = (ORIG_SIZE + SECTOR - 1) // SECTOR   # 71

def main():
    iso_path = sys.argv[1]
    with open(iso_path, "r+b") as iso:
        head = iso.read(6 * 1024 * 1024)

        # verify original JP COMPDATA still present at ORIG_LBA
        iso.seek(ORIG_LBA * SECTOR)
        cur = iso.read(ORIG_SIZE)
        ref = open(r"E:\Projects\SRW Z\_work\extracted\DATA_COMPDATA.BN", "rb").read()
        print("original COMPDATA intact at LBA %d? %s" % (ORIG_LBA, cur == ref))
        if cur != ref:
            print("  !! ORIG_LBA content differs from extracted original - restoring content too")
            iso.seek(ORIG_LBA * SECTOR)
            iso.write(ref + b"\x00" * (ORIG_SECTORS * SECTOR - len(ref)))

        # 1) ISO9660 dir record
        p = head.find(b"COMPDATA.BN;1")
        assert p > 0, "dir record not found"
        rec = p - 33
        cur_lba = struct.unpack_from("<I", head, rec + 2)[0]
        print("dir record current LBA %d (relocated=%s)" % (cur_lba, cur_lba == NEW_LBA))
        iso.seek(rec + 2);  iso.write(struct.pack("<I", ORIG_LBA))
        iso.seek(rec + 6);  iso.write(struct.pack(">I", ORIG_LBA))
        iso.seek(rec + 10); iso.write(struct.pack("<I", ORIG_SIZE))
        iso.seek(rec + 14); iso.write(struct.pack(">I", ORIG_SIZE))
        print("dir record -> LBA %d size %d" % (ORIG_LBA, ORIG_SIZE))

        # 2) internal file table (\DATA\COMPDATA.BN ... [u32 LBA][u32 sectors] at +0x20)
        cn = head.find(b"COMPDATA.BN;1")
        while cn >= 0:
            if head[cn - 8:cn] == b"\\\\DATA\\\\":
                tbl_lba = struct.unpack_from("<I", head, cn + 0x20)[0]
                print("file table current LBA %d (relocated=%s)" % (tbl_lba, tbl_lba == NEW_LBA))
                iso.seek(cn + 0x20); iso.write(struct.pack("<I", ORIG_LBA))
                iso.seek(cn + 0x24); iso.write(struct.pack("<I", ORIG_SECTORS))
                print("file table -> LBA %d, %d sectors" % (ORIG_LBA, ORIG_SECTORS))
                break
            cn = head.find(b"COMPDATA.BN;1", cn + 1)
        else:
            raise SystemExit("internal file-table entry for COMPDATA not found")
    print("COMPDATA relocation reverted (points back to original JP file).")

if __name__ == "__main__":
    main()
