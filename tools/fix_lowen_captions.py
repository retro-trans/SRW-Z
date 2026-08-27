# -*- coding: utf-8 -*-
"""Normalise every spelling of レーベン to Lowen in the battle captions.

The companion to fix_lowen.py, which handles STAGE.BIN. The captions live in
/BTL/SRVC.BIN - uncompressed, so this is a byte pass rather than a record
rebuild - and SRVC exists TWICE in the image (the original extent and the
relocated copy srvc_apply --free created), so every occurrence in the whole
image is fixed rather than one file's.

    Reeven  126
    Raben    18
    Leben     2

Caption fields are variable-length and NUL-terminated back to back, and are
reached by ABSOLUTE pointers rather than by scanning, so a shorter name simply
NUL-pads the tail of its own field: the following field keeps its address and is
never touched. Nothing here grows - every variant is 5 or 6 characters against
Lowen's 5.

STAGE is skipped because it is banlz-compressed; fix_lowen.py does that half,
and conditions each row on its JAPANESE containing レーベン. Here there is no
aligned japanese to condition on, so only the variants that CANNOT be an
ordinary English word are renamed. "Raven", "Lane" and the like are deliberately
left to the STAGE pass.

Usage: fix_lowen_captions.py <iso> [--write]
"""
import re
import sys

GOOD = b"Lowen"
VARIANTS = [b"Reeven", b"Raben", b"Leben"]
STAGE_LBA, STAGE_SIZE = 1651029, 3910128
SECTOR = 2048


def field(buf, i):
    """The printable NUL-terminated caption containing buf[i], or None."""
    s = buf.rfind(b"\x00", max(0, i - 400), i) + 1
    e = buf.find(b"\x00", i)
    if e < 0 or e - s < 4 or e - s > 400:
        return None
    t = buf[s:e]
    ok = sum(1 for c in t if 32 <= c < 127 or c == 0x5C)
    if ok < len(t) * 0.75:
        return None
    return s, e, t


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    lo, hi = STAGE_LBA * SECTOR, STAGE_LBA * SECTOR + STAGE_SIZE
    f = open(iso, "r+b" if write else "rb")
    CH = 1 << 24
    off, prev, edits, seen = 0, b"", [], set()
    while True:
        b = f.read(CH)
        if not b:
            break
        buf = prev + b
        base = off - len(prev)
        for v in VARIANTS:
            i = buf.find(v)
            while i >= 0:
                p = base + i
                if not (lo <= p < hi):
                    r = field(buf, i)
                    if r is not None:
                        s, e, t = r
                        if base + s not in seen:
                            seen.add(base + s)
                            new = t
                            for w in VARIANTS:
                                new = re.sub(br"\b%s\b" % w, GOOD, new)
                            if new != t:
                                assert len(new) <= len(t)
                                edits.append((base + s, e - s, t, new))
                i = buf.find(v, i + 1)
        prev = buf[-512:]
        off += len(b)

    tally = {}
    for _p, _n, t, new in edits:
        for w in VARIANTS:
            n = len(re.findall(br"\b%s\b" % w, t))
            if n:
                tally[w] = tally.get(w, 0) + n
    print("caption fields to fix: %d" % len(edits))
    for w in VARIANTS:
        if tally.get(w):
            print("   %-8s %d" % (w.decode(), tally[w]))
    for p, n, t, new in edits[:6]:
        print("   LBA %-9d %r -> %r" % (p // SECTOR, t[:44].decode("cp932", "ignore"),
                                        new[:44].decode("cp932", "ignore")))
    if not write or not edits:
        if not write:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return
    for p, n, t, new in edits:
        f.seek(p)
        assert f.read(n) == t, "moved under us at %#x" % p
        f.seek(p)
        f.write(new + b"\x00" * (n - len(new)))
    f.close()
    g = open(iso, "rb")
    bad = 0
    for p, n, t, new in edits:
        g.seek(p)
        if g.read(len(new)) != new:
            bad += 1
    g.close()
    print("\nwritten; verified %d of %d" % (len(edits) - bad, len(edits)))


if __name__ == "__main__":
    main()
