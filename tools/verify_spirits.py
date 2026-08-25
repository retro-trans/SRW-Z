# -*- coding: utf-8 -*-
"""Assert no two spirit commands share a name.

Born 2026-08-25: the Analyze spirit displayed as "Scan", so TWO spirits both
read "Scan" - one reveals enemy stats, the other cuts enemy attack and defense
by 10%. `ui_batch2.py` had `0x337408: "Analyze"` all along; the patch never
reached the image and "Analyze" appeared nowhere in the ELF.

Why this check and not a broader one - both broader forms were tried and both
drown in false positives:

  * diffing ui_batch*.py against the ELF gives 433 hits, nearly all the
    deliberate fullwidth conversion ('.' -> U+FF0E, digits -> U+FF10+) that the
    menu renderer REQUIRES, plus ~58 deliberate shortenings to fit fixed slots
    (Chain Attack -> Chain Atk, Courage -> Brave). The batch files are the
    intent; the image is downstream of fitting passes.
  * duplicate short strings anywhere in the ELF gives 124 hits, nearly all
    legitimate shared menu labels (Unit, Pilot, Yes, OK, Repair).

Inside the spirit record table, though, a repeated name is always a bug.

Table at 0x3FA290, stride 0x10 = [name_va, kanji_va, desc_va, ?].

Usage: verify_spirits.py <iso> [--strict]
"""
import collections
import struct
import sys

ELF_LBA, ELF_LEN, SEC = 455, 3471624, 2048
VBASE, FOFF = 0x100000, 0x1A80
TABLE_VA, STRIDE, MAXROWS = 0x3FA290, 0x10, 64


def main():
    iso = sys.argv[1]
    strict = "--strict" in sys.argv
    f = open(iso, "rb")
    f.seek(ELF_LBA * SEC)
    elf = f.read(ELF_LEN)
    f.close()

    def s_at_va(va):
        off = va - VBASE + FOFF
        if not (0 <= off < len(elf)):
            return None
        e = elf.find(b"\x00", off)
        try:
            return elf[off:e].decode("cp932")
        except Exception:
            return None

    base = TABLE_VA - VBASE + FOFF
    rows = []
    for i in range(MAXROWS):
        o = base + i * STRIDE
        if o + 8 > len(elf):
            break
        nm_va = struct.unpack_from("<I", elf, o)[0]
        if not (0x300000 < nm_va < 0x500000):
            continue
        nm = s_at_va(nm_va)
        if nm:
            rows.append((i, nm_va, nm))

    counts = collections.Counter(n for _, _, n in rows)
    dups = sorted(n for n, c in counts.items() if c > 1)
    print("spirit records      : %d" % len(rows))
    print("duplicate names     : %d" % len(dups))
    if dups:
        print("\nFAIL - a repeated spirit name is always a bug:")
        for d in dups:
            where = ["%#x" % va for i, va, n in rows if n == d]
            print("   %-16s at %s" % (d, " ".join(where)))
        if strict:
            sys.exit(1)
    else:
        print("OK - every spirit has a distinct name")


if __name__ == "__main__":
    main()
