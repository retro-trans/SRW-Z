# -*- coding: utf-8 -*-
u"""Word-level renames in the SRVC battle captions, byte length preserved.

A caption may NOT change length: scripted attack sequences fetch their lines by
byte offset from tables this does not rebuild, so one longer string slides every
offset after it in its block. fix_srvc_names.py handles that by only allowing
replacements of exactly equal length; this one also allows SHORTER, padding the
caption with trailing spaces back to its original byte count. A longer
replacement is refused outright.

Renames here are the Xabungle names, settled by the user 2026-09-10 against
akurasu (see fix_plate_spellings.py for the full note). All four are the same
length or shorter, which is what lets them reach this pool at all:

    Elche  -> Elchi   (same)      Kotsett -> Cotset  (-1)
    Hora   -> Hola    (same)      Daiku   -> Dike    (-1)

Every hit is verified to sit inside a printable NUL-terminated caption, and the
whole image is swept, so the relocated second copy of SRVC is covered too.

Usage: fix_srvc_words.py <iso> [--write]
"""
import re
import sys

PAIRS = [("Elche", "Elchi"), ("Hora", "Hola"),
         ("Kotsett", "Cotset"), ("Daiku", "Dike")]


def caption_at(buf, i):
    """The whole NUL-terminated printable caption containing buf[i], or None."""
    s = buf.rfind(b"\x00", max(0, i - 400), i) + 1
    e = buf.find(b"\x00", i)
    if e < 0 or e - s < 4 or e - s > 400:
        return None
    t = buf[s:e]
    ok = sum(1 for c in t if 32 <= c < 127 or c == 0x5C)
    return (s, t) if ok >= len(t) * 0.75 else None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    rx = [(re.compile(br"(?<![A-Za-z])" + a.encode() + br"(?![A-Za-z])"),
           b.encode(), a, b) for a, b in PAIRS]
    f = open(iso, "r+b" if write else "rb")
    CH = 1 << 24
    off, prev, edits = 0, b"", {}
    while True:
        blk = f.read(CH)
        if not blk:
            break
        buf = prev + blk
        base = off - len(prev)
        for pat, rep, a, b in rx:
            m = pat.search(buf)
            while m:
                cap = caption_at(buf, m.start())
                if cap:
                    s, t = cap
                    new = t
                    for p2, r2, _, _ in rx:
                        new = p2.sub(r2, new)
                    if len(new) < len(t):
                        new = new + b" " * (len(t) - len(new))
                    if len(new) == len(t) and new != t:
                        edits[base + s] = (t, new)
                m = pat.search(buf, m.start() + 1)
        prev = buf[-512:]
        off += len(blk)
    print("captions to fix: %d" % len(edits))
    for pos, (t, new) in sorted(edits.items())[:10]:
        print("   %#012x %-42s -> %s"
              % (pos, t.decode("cp932", "replace"), new.decode("cp932", "replace")))
    if len(edits) > 10:
        print("   ... and %d more" % (len(edits) - 10))
    if not write or not edits:
        if not write:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return 0
    for pos, (t, new) in edits.items():
        f.seek(pos)
        assert f.read(len(t)) == t, "moved under us at %#x" % pos
        f.seek(pos)
        f.write(new)
    f.close()
    g = open(iso, "rb")
    bad = 0
    for pos, (t, new) in edits.items():
        g.seek(pos)
        if g.read(len(new)) != new:
            bad += 1
    g.close()
    print("written and re-read: %d ok, %d bad" % (len(edits) - bad, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
