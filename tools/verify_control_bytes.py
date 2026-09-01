# -*- coding: utf-8 -*-
"""No UI string may carry a RAW 0x2E-0x3D byte. Those are CONTROL CODES.

To the menu reader at 0x13A290, bytes 0x2E-0x3D - '.' '/' and '0'-'9', ':' ';'
'<' '=' '>' - are not characters. They are commands. patch.encode(s, "menuhw")
exists precisely to convert them: digits and '.' become private HALF-width cells
(0x8540, 0x8547+), ':' and '/' become their full-width forms. Any raw byte in
that range in a drawn string is a bug that has already happened twice here:

  * "Type100" drew as "TypeDijeh" - it printed "Type", swallowed "100" and the
    NUL as a command plus parameters, and ran on into the next name field.
  * 0.8.113's Back Log footer read "SetsukoUp / SetsukoPrev / SetsukoBack" on
    Setsuko's route and "RandUp / RandPrev / RandBack" on Rand's. I had written
    ":Up" as raw ASCII to save 8px over the 21px full-width colon; 0x3A is the
    code that expands to the protagonist's name.

There is no half-width colon. menuhw maps ':' to 0x8146 and that costs 21px -
plan the layout around it rather than reaching for the ASCII byte.

Usage: verify_control_bytes.py <iso> [--strict]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_ui_strings import ELF_LBA, ELF_LEN, SEC, load_batches

LO, HI = 0x2E, 0x3D


def check_rec6(iso):
    """The NISVDATA help book is drawn by the same 0x13A290 reader, so its
    runs are under the same rule.  It is not in the ELF batches, so it has to
    be walked separately."""
    import banlz
    import nisv_rec6
    f = open(iso, "rb")
    f.seek(1568269 * SEC)
    items = banlz.decompress_all(f.read(272 * SEC))
    f.close()
    secs, _ = nisv_rec6.parse(bytes(items[6][1]))
    checked, bad = 0, []
    for s in secs:
        if s.runs is None:
            continue
        for r in s.runs:
            raw = r.text.encode("cp932")
            checked += 1
            hits, i = set(), 0
            while i < len(raw):
                c = raw[i]
                if 0x81 <= c <= 0xFC:        # cp932 lead byte: skip the pair
                    i += 2
                    continue
                if LO <= c <= HI:
                    hits.add(c)
                i += 1
            if hits:
                bad.append(("rec6/sec%d" % s.index, r.y, raw, sorted(hits)))
    return checked, bad


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(ELF_LBA * SEC)
    elf = f.read(ELF_LEN)
    f.close()

    checked, bad = 0, []
    for name, batch in load_batches():
        for off, want in sorted(batch.items()):
            if not isinstance(off, int) or not isinstance(want, str):
                continue
            e = elf.find(b"\x00", off)
            if e < 0:
                continue
            raw = elf[off:e]
            if not raw:
                continue
            checked += 1
            hits = sorted({b for b in raw if LO <= b <= HI})
            if hits:
                bad.append((name, off, raw, hits))

    n6, bad6 = check_rec6(iso)
    checked += n6
    bad += bad6

    print("%d drawn UI strings checked for raw control bytes" % checked)
    if not bad:
        print("control-byte gate OK: none carry a raw 0x2E-0x3D")
        return 0
    print("FAIL: %d string(s) carry a raw control byte" % len(bad))
    for name, off, raw, hits in bad[:30]:
        print("   %-12s %#08x  %-24r  raw %s"
              % (name, off, raw.decode("cp932", "replace"),
                 " ".join("%02X" % h for h in hits)))
    print("\nRun the text through patch.encode(s, 'menuhw') instead of "
          "str.encode('cp932').")
    return 1


if __name__ == "__main__":
    sys.exit(main())
