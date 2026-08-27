# -*- coding: utf-8 -*-
"""Undo tools/test_weapon_shift.py.

The experiment proved the weapon list is addressed by STORED OFFSETS: growing
'MusouSw' to 'Musou Sword' left the next entry's offset pointing 8 bytes into
the new string, and the game rendered

    Musou Sword
    ord            <- bytes 8..10 of "Musou Sword", read from 0x66f50

so the change must come out. This restores the exact original layout:

    0x66f48  'MusouSw'       slot 8   (was grown to 16)
    0x66f50  'Hissatsu Musou'         (shifts back -8)
    0x66f60  'Sigma Breast Musou Sword'
    0x66f80  'Trinity Wing'  slot 24  (was shrunk to 16 to donate the bytes)

Usage: revert_weapon_shift.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, NSEC = 1823000, 74
NUL = b"\x00"
T = 0x66F48


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(NSEC * SEC))
    rec = bytearray(banlz.decompress_all(bytes(raw))[0][1])

    if bytes(rec[T:T + 11]) != b"Musou Sword":
        print("nothing to revert: %r at %#x"
              % (bytes(rec[T:T + 12]).decode("cp932", "ignore"), T))
        f.close()
        return

    middle = bytes(rec[T + 16:T + 16 + 0x30])       # the two shifted entries
    q = T
    rec[q:q + 8] = b"MusouSw" + NUL
    q += 8
    rec[q:q + len(middle)] = middle
    q += len(middle)
    rec[q:q + 24] = b"Trinity Wing" + NUL * 12
    q += 24

    p = T
    for _ in range(6):
        e = rec.find(NUL, p)
        k = e
        while k < len(rec) and rec[k] == 0:
            k += 1
        print("   %#08x slot=%-3d %r"
              % (p, k - p, bytes(rec[p:e]).decode("cp932", "ignore")))
        p = k

    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return

    blob = banlz.compress_record_optimal(bytes(rec))
    if len(blob) > NSEC * SEC:
        print("REFUSED: recompressed %d > slot %d" % (len(blob), NSEC * SEC))
        f.close()
        sys.exit(1)
    out = bytearray(NSEC * SEC)
    out[:len(blob)] = blob
    f.seek(LBA * SEC)
    f.write(bytes(out))
    f.close()
    g = open(iso, "rb")
    g.seek(LBA * SEC)
    chk = banlz.decompress_all(bytes(bytearray(g.read(NSEC * SEC))))
    g.close()
    assert bytes(chk[0][1]) == bytes(rec), "readback mismatch"
    print("\nreverted and verified")


if __name__ == "__main__":
    main()
