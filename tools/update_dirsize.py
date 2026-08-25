"""Patch the ISO9660 directory-record data-length for a file so the emulator
loads the full (grown) ELF. Usage: update_dirsize.py <iso> <NAME> <newsize>
Scans the root directory extent (from the PVD at LBA 16) for the 8.3 name and
rewrites the 8-byte size field (LE u32 at rec+10, BE u32 at rec+14).
"""
import sys, struct

SECTOR = 2048


def main():
    iso_path, name, newsize = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
    with open(iso_path, "r+b") as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        assert pvd[1:6] == b"CD001", "not a PVD"
        root = pvd[156:156 + 34]                       # root directory record
        root_lba = struct.unpack("<I", root[2:6])[0]
        root_len = struct.unpack("<I", root[10:14])[0]
        f.seek(root_lba * SECTOR)
        dirdata = f.read(((root_len + SECTOR - 1) // SECTOR) * SECTOR)
        target = name.encode()
        i = 0
        while i < len(dirdata):
            rlen = dirdata[i]
            if rlen == 0:
                i = (i // SECTOR + 1) * SECTOR           # next sector
                continue
            namelen = dirdata[i + 32]
            fn = dirdata[i + 33:i + 33 + namelen]
            # ISO names often have ";1" version suffix
            base = fn.split(b";")[0]
            if base == target:
                cur = struct.unpack("<I", dirdata[i + 10:i + 14])[0]
                recoff = root_lba * SECTOR + i
                f.seek(recoff + 10)
                f.write(struct.pack("<I", newsize) + struct.pack(">I", newsize))
                print("patched %s dir-record @%#x: size %d -> %d" % (name, recoff, cur, newsize))
                return
            i += rlen
        print("NOT FOUND:", name)
        sys.exit(1)


if __name__ == "__main__":
    main()
