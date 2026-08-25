# -*- coding: utf-8 -*-
"""Targeted battle-caption line corrections (post-review).

Each entry replaces EVERY occurrence of a caption field body, space-padded
to the original extent (field starts must not move - voice-sync offsets).
Encoding rules: fullwidth 8143=， 8144=． 8163=… ; '\\n' is the literal
two ASCII bytes; ASCII '.' ',' are caption CONTROL codes - never emit.

2026-08-20 fixes (user review, JP cross-checked via index-aligned
srwz_jpall.bin):
  了解、牽制しておくわ！ was rendered "I'll hold back." - kensei means
  suppressing the ENEMY: -> "Roger, covering fire!"
  悪いけど…いただきっ！ was clipped to "mine!": -> "Sorry... I'll take it!"

Usage: srvc_line_fixes.py <iso>   (idempotent)
"""
import sys

SRVC_LBA, SECTOR, SECTORS = 1826000, 2048, 1624

FW_C = b"\x81\x43"   # ，
FW_P = b"\x81\x44"   # ．
ELL = b"\x81\x63"    # …
OQ, CQ = b"\x81\x75", b"\x81\x76"

FIXES = [
    (b'"Roger' + FW_C + b"I'll hold back" + FW_P + b'"',
     b'"Roger' + FW_C + b'covering fire!"'),
    (OQ + b"Sorry" + FW_C + b"but" + ELL + b"\\nmine!" + CQ,
     OQ + b"Sorry" + ELL + b"\\nI'll take it!" + CQ),
]


def main():
    iso = open(sys.argv[1], "r+b")
    iso.seek(SRVC_LBA * SECTOR)
    d = bytearray(iso.read(SECTORS * SECTOR))
    total = 0
    for old, new in FIXES:
        n = 0
        i = 0
        while True:
            i = d.find(old, i)
            if i < 0:
                break
            # extent = old body + trailing spaces
            j = i + len(old)
            while j < len(d) and d[j] == 0x20:
                j += 1
            extent = j - i
            assert len(new) <= extent, (len(new), extent, old)
            d[i:j] = new + b" " * (extent - len(new))
            n += 1
            i = j
        print("%r -> %r : %d occurrence(s)" % (old, new, n))
        total += n
    iso.seek(SRVC_LBA * SECTOR)
    iso.write(bytes(d))
    iso.close()
    print("done, %d fields fixed" % total)


if __name__ == "__main__":
    main()
