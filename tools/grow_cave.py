# -*- coding: utf-8 -*-
"""Grow the font cave segment into the ELF's last-sector slack.

The cave is PT_LOAD[208] (file 0x34D770, vaddr 0x78A070) and it ends EXACTLY at
the end of the ELF. The ELF occupies 1696 sectors with 1784 bytes unused in the
final one, so the segment can be extended without moving the file or touching
any other extent - only three declared sizes change:

  1. PT_LOAD[208].p_filesz and .p_memsz          (in the ELF header)
  2. the ISO9660 directory record's data length  (BOTH-ENDIAN: LE at +10 and
     BE at +14 - ISO9660 stores every multi-byte field twice, and a loader that
     reads the big-endian copy would otherwise see the old size)
  3. nothing else - the ELF is loaded by the PS2 BIOS through ISO9660, not
     through the game's own file table

Everything appended is zero, so the new space is inert until something is put
there. This is deliberately a SEPARATE step from using it: grow, build, confirm
the game still boots, and only then move data in. If it does not boot, nothing
else has changed and the revert is exact.

Usage: grow_cave.py <iso> [--bytes N] [--write] [--revert]
"""
import struct
import sys

ELF_LBA = 455
ORIG_SIZE = 3471624
PH_INDEX = 208
DIR_LBA, DIR_OFF = 261, 0x146
SECTOR = 2048


def read_elf(f, size):
    f.seek(ELF_LBA * SECTOR)
    return bytearray(f.read(size))


def dir_size(f):
    f.seek(DIR_LBA * SECTOR)
    sec = bytearray(f.read(SECTOR))
    le = struct.unpack_from("<I", sec, DIR_OFF + 10)[0]
    be = struct.unpack_from(">I", sec, DIR_OFF + 14)[0]
    return sec, le, be


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    revert = "--revert" in sys.argv
    n = int(sys.argv[sys.argv.index("--bytes") + 1]) if "--bytes" in sys.argv else 1088
    if n % 4:
        raise SystemExit("--bytes must be a multiple of 4")

    f = open(iso, "r+b" if write else "rb")
    sec, le, be = dir_size(f)
    print("ISO dir record: size LE %d, BE %d %s" % (le, be, "(agree)" if le == be else "(MISMATCH)"))
    if le != be:
        raise SystemExit("directory record is inconsistent - refusing")

    cur = le
    elf = read_elf(f, cur)
    phoff = struct.unpack_from("<I", elf, 0x1C)[0]
    o = phoff + PH_INDEX * 32
    typ, poff, vaddr, paddr, filesz, memsz, flags, align = struct.unpack_from("<8I", elf, o)
    print("PT_LOAD[%d]: off %#x vaddr %#x filesz %#x memsz %#x"
          % (PH_INDEX, poff, vaddr, filesz, memsz))
    if poff + filesz != cur:
        raise SystemExit("cave does not end at the file end (%#x vs %#x)"
                         % (poff + filesz, cur))

    sectors = (cur + SECTOR - 1) // SECTOR
    slack = sectors * SECTOR - cur
    print("ELF %d bytes in %d sectors, slack %d" % (cur, sectors, slack))

    if revert:
        delta = cur - ORIG_SIZE
        if delta <= 0:
            print("already at the original size")
            return
        new_size = ORIG_SIZE
        n = -delta
    else:
        if cur != ORIG_SIZE:
            print("already grown by %d bytes - revert first" % (cur - ORIG_SIZE))
            return
        if n > slack:
            raise SystemExit("cannot grow %d: only %d bytes of slack" % (n, slack))
        new_size = cur + n

    struct.pack_into("<I", elf, o + 16, filesz + n)      # p_filesz
    struct.pack_into("<I", elf, o + 20, memsz + n)       # p_memsz
    print("cave filesz/memsz %#x -> %#x   (vaddr %#x .. %#x)"
          % (filesz, filesz + n, vaddr, vaddr + filesz + n))
    print("ELF size %d -> %d" % (cur, new_size))
    if not write:
        print("\n(dry run - pass --write to apply)")
        return

    f.seek(ELF_LBA * SECTOR)
    f.write(bytes(elf))
    if n > 0:
        f.seek(ELF_LBA * SECTOR + cur)
        f.write(b"\x00" * n)
    struct.pack_into("<I", sec, DIR_OFF + 10, new_size)
    struct.pack_into(">I", sec, DIR_OFF + 14, new_size)
    f.seek(DIR_LBA * SECTOR)
    f.write(bytes(sec))
    f.close()

    g = open(iso, "rb")
    s2, le2, be2 = dir_size(g)
    e2 = read_elf(g, new_size)
    g.close()
    assert le2 == be2 == new_size, "dir record readback"
    t = struct.unpack_from("<8I", e2, o)
    assert t[4] == filesz + n and t[5] == memsz + n, "phdr readback"
    print("written and verified: dir record %d, cave filesz %#x" % (le2, t[4]))


if __name__ == "__main__":
    main()
