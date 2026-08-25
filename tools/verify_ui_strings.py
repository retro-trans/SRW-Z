# -*- coding: utf-8 -*-
"""Assert every ELF UI string in ui_batch*.py actually reached the image.

Born 2026-08-25: the Analyze spirit displayed as "Scan". `ui_batch2.py` had the
right value at 0x337408 all along - the patch simply never landed, and the word
"Analyze" appeared NOWHERE in the ELF. Nothing checked for that:
verify_elf_patches.py tests nine hand-picked words and five byte patterns, so
1302 UI strings across nine batch files had no gate at all.

Two of this project's bugs have now been "the fix existed but never reached the
image" (this one and the literal backslash-n). A tool being correct is not
evidence that its output shipped - only the image is.

Each BATCH maps a FILE OFFSET in the ELF to the English string that belongs
there. This reads the ELF out of the ISO and compares, NUL-terminated.

Usage:
  verify_ui_strings.py <iso>            report
  verify_ui_strings.py <iso> --strict   exit 1 on any mismatch
"""
import glob
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ELF_LBA, ELF_LEN, SEC = 455, 3471624, 2048


# The ELF UI is drawn by the MENU renderer (0x13A290) where ASCII 0x2E-0x3D are
# CONTROL CODES, so a later pass deliberately converts '.' '/' and digits to
# their fullwidth cells. The batch files still hold the pre-conversion ASCII, so
# compare NORMALISED - otherwise every converted string reads as a mismatch.
FW = {}
for _a, _b in zip(u"．！？，／：；＜＝＞",
                  u".!?,/:;<=>"):
    FW[_a] = _b
for _i in range(10):
    FW[unichr(0xFF10 + _i) if str is bytes else chr(0xFF10 + _i)] = str(_i)


def norm(s):
    return "".join(FW.get(c, c) for c in s)


def load_batches():
    out = []
    here = os.path.dirname(os.path.abspath(__file__))
    for p in sorted(glob.glob(os.path.join(here, "ui_batch*.py"))):
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            mod = importlib.import_module(name)
        except Exception as e:
            print("  !! %s did not import: %s" % (name, e))
            continue
        b = getattr(mod, "BATCH", None)
        if isinstance(b, dict):
            out.append((name, b))
    return out


def main():
    iso = sys.argv[1]
    strict = "--strict" in sys.argv
    f = open(iso, "rb")
    f.seek(ELF_LBA * SEC)
    elf = f.read(ELF_LEN)
    f.close()

    total = ok = miss = unenc = 0
    bad = []
    for name, batch in load_batches():
        for off, want in sorted(batch.items()):
            if not isinstance(off, int) or not isinstance(want, str):
                continue
            total += 1
            try:
                wb = want.encode("cp932")
            except Exception:
                unenc += 1
                bad.append((name, off, want, "<not cp932-encodable>"))
                continue
            if off + len(wb) > len(elf):
                bad.append((name, off, want, "<past end of ELF>"))
                miss += 1
                continue
            e = elf.find(b"\x00", off)
            got_b = elf[off:e if e != -1 else off + len(wb)]
            try:
                got = got_b.decode("cp932")
            except Exception:
                got = repr(got_b)
            if got_b == wb or norm(got) == norm(want):
                ok += 1
            else:
                miss += 1
                bad.append((name, off, want, got))

    print("UI strings declared : %d" % total)
    print("  present in the ELF: %d" % ok)
    print("  MISSING / differ  : %d" % miss)
    if unenc:
        print("  not cp932-encodable: %d" % unenc)
    if bad:
        print("\n=== first 25 mismatches ===")
        for name, off, want, got in bad[:25]:
            print("  %-14s %#08x" % (name, off))
            print("      want: %r" % want[:60])
            print("      got : %r" % got[:60])
        if len(bad) > 25:
            print("  ... %d more" % (len(bad) - 25))
    if strict and bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
