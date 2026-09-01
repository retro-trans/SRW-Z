# -*- coding: utf-8 -*-
"""Apply the srvc_line_fixes table across the WHOLE image, not just BTL_SRVC.

Why this exists. srvc_line_fixes.py rewrites the caption pool at LBA 1826000.
On 2026-08-31 a screenshot showed a caption still using its OLD wrap even
though the pool at 1826000 already held the corrected text - because the same
caption strings exist a SECOND time, around LBA 1313725, and nothing in the
srvc toolchain touches that region. Whichever copy the game actually reads,
both now say the same thing.

Only same-length replacements are allowed. A caption field start may not move
(voice-sync offsets are absolute), and a whole-image scan has no field table
to consult, so length equality is the guard that keeps a blind replace safe.

Usage: srvc_line_fixes_all.py <iso> [--dry-run]   (idempotent)
"""
import sys

from srvc_line_fixes import FIXES

CHUNK = 64 * 1024 * 1024
SECTOR = 2048


def main():
    iso, dry = sys.argv[1], "--dry-run" in sys.argv
    # A shorter replacement is padded with trailing spaces to the original
    # extent - the same thing srvc_line_fixes.py does, and the reason a field
    # start never moves. A LONGER one would overwrite the next field, so it is
    # refused outright rather than guessed at.
    # A LONGER replacement is legal for srvc_line_fixes.py, which knows each
    # field's full extent (string + NUL padding) and can spend it. A blind
    # whole-image scan has no field table, so it cannot know where the next
    # field starts and must not guess: those entries are skipped and named,
    # never truncated to fit.
    pairs, skipped = [], []
    for old, new in FIXES:
        if len(new) > len(old):
            skipped.append((old, new))
        else:
            pairs.append((old, new + b" " * (len(old) - len(new))))
    FIXES[:] = pairs
    for old, new in skipped:
        print("SKIPPED (needs the field extent, run srvc_line_fixes.py): %r"
              % old[:44].decode("cp932", "replace"))
    f = open(iso, "rb" if dry else "r+b")
    total = 0
    for old, new in FIXES:
        hits, prev, base = [], b"", 0
        f.seek(0)
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            buf = prev + b
            q = 0
            while True:
                q = buf.find(old, q)
                if q < 0:
                    break
                hits.append(base - len(prev) + q)
                q += 1
            prev = buf[-len(old):]
            base += len(b)
        for h in hits:
            if not dry:
                f.seek(h)
                f.write(new)
            total += 1
        print("%-46s %d occurrence(s)%s"
              % (old[:44].decode("cp932", "replace"), len(hits),
                 "" if hits else "  (already applied or absent)"))
        for h in hits:
            print("      off %#x = LBA %d + %#x" % (h, h // SECTOR, h % SECTOR))
    f.close()
    print("%s %d field(s)" % ("would fix" if dry else "fixed", total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
