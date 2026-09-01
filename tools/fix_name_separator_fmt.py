# -*- coding: utf-8 -*-
"""Make the foreign-name separator a space instead of a middle dot.

The flag at head+67 is not "display order", it is NAME KIND:

    flag 1   field2 + field3      japanese name - \u515c\u7532\u5150, no separator
    flag 0   field3 \u30fb field2      foreign name  - \u30a2\u30e0\u30ed\u30fb\u30ec\u30a4, middle dot

A middle dot between a given name and a surname is correct japanese
typography and wrong in english, so branch B's format is simply the wrong
punctuation for this translation - the ORDER it produces is already right.

This is why the protagonist kept a dot after every other fix. Their record is
built at 0x195aac from the name-entry buffer in the save, in japanese order
with flag 0, so it takes branch B - and no data pass can reach a save.
Changing the format reaches it, because the format is in the executable.

Simulated over every record before applying: 32 records / 14 distinct pairs
are still on branch B, and all 14 read correctly with a space -
'Andrew\u30fbWaltfeld' -> 'Andrew Waltfeld', 'Mu\u30fbLa Fraga' -> 'Mu La Fraga',
'Gym\u30fbGhingnham' -> 'Gym Ghingnham'. None has an empty half, so no pair is
left with a stray leading or trailing space. Flag-1 records use a different
format and are untouched.

VA 0x442710 is referenced exactly once in the whole ELF, from branch B at
0x35f1ac, so nothing but names can be affected.

'\u30fb' is two bytes and ' ' is one, so the string shrinks inside its 8-byte
slot and the slack is zero-filled.

Usage: fix_name_separator_fmt.py <iso> [--write]
"""
import sys

LBA, VBASE, FOFF = 455, 0x100000, 0x1A80
VA = 0x442710
OLD = b"%s\x81\x45%s\x00"
NEW = b"%s %s\x00"


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    off = LBA * 2048 + VA - VBASE + FOFF
    f = open(iso, "r+b" if write else "rb")
    f.seek(off)
    got = f.read(len(OLD))
    if got == NEW + b"\x00":
        print("already patched: %#08x = %r" % (VA, NEW))
        f.close()
        return 0
    if got != OLD:
        f.close()
        raise SystemExit("REFUSING: %#08x holds %r, expected %r" % (VA, got, OLD))
    print("%#08x  %r  ->  %r" % (VA, OLD, NEW))
    if not write:
        f.close()
        print("(dry run - pass --write to apply)")
        return 0
    f.seek(off)
    f.write(NEW + b"\x00" * (len(OLD) - len(NEW)))
    f.close()
    print("patched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
