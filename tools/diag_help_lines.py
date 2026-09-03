# -*- coding: utf-8 -*-
u"""Diagnostic: what does the ability DATA HELP panel do with line 2?

OBSERVED, in our build:

    Tri Charge   1 line  in the data -> 1 line  on screen
    Mazin Power  2 lines in the data -> line 1 only
    Unite        4 lines in the data -> lines 1, 3 and 4

and the JAPANESE disc renders マジンパワー's two lines correctly, so this is
ours, not stock. It is also not our re-wrapping: 26 of 51 descriptions have
more lines than the japanese, but Mazin Power has exactly the same count (2 and
2) and still loses one.

The suspect is patch_hwfont's MHOOK at 0x13A7A0 -> cave 0x78A528. s4 is the
SOURCE STRING POINTER (0x13a5f8 `lbu a0,0(s4)` / 0x13a60c `addiu s4,s4,1`), and
the hook does `addiu s4,s4,-1` whenever it remaps an ASCII byte - rewinding one
byte because a half-width character is 1 byte where the reader consumed 2. That
is right in principle, but it is the only thing in this path the japanese build
does not do.

Reading further did not settle HOW that drops a whole line rather than a single
character, so this replaces one description with three short, equal, obviously
distinguishable lines. Short so that width cannot be the variable, distinct so
the answer is unambiguous:

    AAAAA        -> all three shown : line loss is content- or width-dependent
    BBBBB        -> A and C shown   : line 2 is dropped, full stop
    CCCCC        -> A only shown    : it stops at the first newline

Reversible: --revert puts the real description back.

Usage: diag_help_lines.py <iso> [--write] [--revert]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
COMP_LBA, COMP_NSEC = 1823000, 74

REAL = u"Activates at Will １３０+．\nFinal damage dealt x１．２５．"
DIAG = u"AAAAA\nBBBBB\nCCCCC"


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    revert = "--revert" in sys.argv
    old, new = (DIAG, REAL) if revert else (REAL, DIAG)
    ob, nb = old.encode("cp932"), new.encode("cp932")

    f = open(iso, "r+b" if write else "rb")
    f.seek(COMP_LBA * SEC)
    raw = bytearray(f.read(COMP_NSEC * SEC))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    hdr, data = live[0][0], bytearray(live[0][1])

    k = data.find(ob)
    if k < 0:
        print("not found - already in the %s state?" % ("real" if revert else "diag"))
        f.close()
        return 1
    z = data.find(b"\x00", k)
    e = z
    while e < len(data) and data[e] == 0:
        e += 1
    slot = e - k - 1
    print("description @%#x: %d bytes used, slot %d" % (k, z - k, slot))
    assert len(nb) <= slot, "replacement needs %d, slot %d" % (len(nb), slot)
    data[k:k + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
    print("  %r\n  -> %r" % (ob, nb))

    blob = banlz.compress_record(bytes(data))
    if len(blob) > COMP_NSEC * SEC:
        blob = banlz.compress_record_optimal(bytes(data))
    assert hdr + len(blob) <= COMP_NSEC * SEC, "COMPDATA overflows its slot"
    if write:
        raw[hdr:hdr + len(blob)] = blob
        f.seek(COMP_LBA * SEC)
        f.write(bytes(raw))
        print("COMPDATA written (%d bytes compressed)" % len(blob))
    else:
        print("(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
