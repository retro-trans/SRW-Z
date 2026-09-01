# -*- coding: utf-8 -*-
"""Kill the middle dot on the THIRD screen that composes a pilot's name.

0.9.7 removed the '\u30fb' from the save/load and hero-select formats, and the
user confirmed "Koji Kabuto" on both. 0.9.8 still drew "Amos\u30fbJiron" somewhere
else, because a third screen composes names through its own routine.

The routine is at VA 0x35f12c, compose_name(a0=record, a1=dest), and it picks
between three branches:

    lb   v0, 69(v1)
    bne  v0, zero, ->C          flag byte right after the three string fields
    ...
    A    "%s%s"   % (field3, field2)   taken when field3 is empty
    B    "%s\u30fb%s" % (field3, field2)   the dotted one - what Jiron gets
    C    "%s%s"   % (field2, field3)   western order, no separator

Note the ARGUMENT ORDER. The two formats fixed in 0.9.7 are called with
(field2, field3); this routine's A and B branches are called with them the
other way round. That is why the data swap that fixed every other screen could
not fix this one, and why simply widening B's format to "%s%s" would have
produced "AmosJiron " - right punctuation, wrong order.

Branch C is already exactly what we want, and the game already runs it. It is
also strictly more general than A and B: field2 carries a TRAILING SPACE, so
C gives "Jiron " + "Amos" = "Jiron Amos", and when either half is empty it
degrades to the other half on its own - which is all A ever did.

So the fix is to stop testing the flag and always take C. One instruction:

    bne v0, zero, 0x35f1b8      ->      b 0x35f1b8

The delay slot is already a nop, so nothing else moves. Records whose flag was
non-zero took C before and take C now - their rendering is unchanged.

Usage: fix_name_dot_screen.py <iso> [--write]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
LBA, ELF_SIZE = 455, 3471624
VA = 0x35F160
OLD = 0x14400015        # bne  v0, zero, 0x35f1b8
NEW = 0x10000015        # b    0x35f1b8


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    off = LBA * 2048 + VA - VBASE + FOFF
    f = open(iso, "r+b" if write else "rb")
    f.seek(off)
    got = struct.unpack("<I", f.read(4))[0]
    if got == NEW:
        print("already patched: %#08x = %08X (b 0x35f1b8)" % (VA, got))
        f.close()
        return 0
    if got != OLD:
        f.close()
        raise SystemExit("REFUSING: %#08x holds %08X, expected %08X"
                         % (VA, got, OLD))
    print("%#08x  %08X  bne v0, zero, 0x35f1b8" % (VA, OLD))
    print("       -> %08X  b   0x35f1b8   (always take the western branch)"
          % NEW)
    if not write:
        f.close()
        print("(dry run - pass --write to apply)")
        return 0
    f.seek(off)
    f.write(struct.pack("<I", NEW))
    f.close()
    print("patched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
