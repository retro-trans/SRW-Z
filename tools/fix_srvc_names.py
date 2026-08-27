# -*- coding: utf-8 -*-
"""Two same-length name fixes in the battle captions.

    Kaimera -> Chimera    カイメラ, 7 bytes for 7
    Raven   -> Lowen      レーベン・ゲネラール, 5 bytes for 5 - a FIFTH spelling of
                          レーベン after Raben, Reeven and Lowen. The caption
                          "I am Raven General! The\nyoung lion of Kaimera!" is
                          「俺はレーベン・ゲネラール！　カイメラの若獅子だ！」

Both replacements are the SAME LENGTH, so this is a byte substitution: no slot
maths, no repointing, no recompression. SRVC exists twice in the image - the
original extent and the relocated copy srvc_apply --free created - so every
occurrence in the whole image is fixed, not just one file's.

Each hit is verified to sit inside a printable NUL-terminated caption before it
is touched, so a coincidental match inside binary data cannot be hit.

Usage: fix_srvc_names.py <iso> [--write]
"""
import sys

PAIRS = [(b"Kaimera", b"Chimera"), (b"Raven", b"Lowen")]


def caption_at(buf, i, n):
    """Is buf[i:i+n] inside a printable NUL-terminated string?"""
    s = buf.rfind(b"\x00", max(0, i - 400), i) + 1
    e = buf.find(b"\x00", i)
    if e < 0 or e - s < 4 or e - s > 400:
        return None
    t = buf[s:e]
    ok = sum(1 for c in t if 32 <= c < 127 or c in (0x5C,))
    return t if ok >= len(t) * 0.75 else None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    CH = 1 << 24
    off, prev, edits = 0, b"", []
    while True:
        b = f.read(CH)
        if not b:
            break
        buf = prev + b
        base = off - len(prev)
        for old, new in PAIRS:
            i = buf.find(old)
            while i >= 0:
                t = caption_at(buf, i, len(old))
                if t is not None:
                    edits.append((base + i, old, new, t.decode("cp932", "ignore")))
                i = buf.find(old, i + 1)
        prev = buf[-512:]
        off += len(b)
    seen = set()
    uniq = []
    for e in edits:
        if e[0] in seen:
            continue
        seen.add(e[0])
        uniq.append(e)
    print("caption hits to fix: %d" % len(uniq))
    for pos, old, new, t in uniq:
        print("   %#012x %-8s -> %-8s %r" % (pos, old.decode(), new.decode(), t[:52]))
    if not write or not uniq:
        if not write:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return
    for pos, old, new, t in uniq:
        f.seek(pos)
        assert f.read(len(old)) == old, "moved under us at %#x" % pos
        f.seek(pos)
        f.write(new)
    f.close()
    g = open(iso, "rb")
    bad = 0
    for pos, old, new, t in uniq:
        g.seek(pos)
        if g.read(len(new)) != new:
            bad += 1
    g.close()
    print("\nwritten; verified %d of %d" % (len(uniq) - bad, len(uniq)))


if __name__ == "__main__":
    main()
