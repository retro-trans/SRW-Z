# -*- coding: utf-8 -*-
"""Leftover bytes after the end of a line - an in-place edit that never padded.

Five fields end with a fragment of themselves repeated:

    ...she's lost her memory, but...).)
    ...Touga and Eiji's situation now...)..)
    ...and Dianna's true intentions.)ions.)
    ...Eina and Luna passed on...).)
    ...is this man...).)

All five are parenthesised thought lines, and the player sees the junk. The
cause is an older pass that wrote a SHORTER string over a longer one without
NUL-padding the remainder, so the tail of the previous text survived past the
new terminator. Every tool here pads the full extent, which is why the defect
stopped at these five: rec9 and rec154 were untouched by any pass this session
and carry it too.

Detected rather than listed: a field is suspect when the text following its
first closing delimiter is itself a suffix of everything up to and including
that delimiter. That is what a truncated overwrite always leaves and what
ordinary text - "Attention! (Ten-hut!)」" - never does.

Also re-wraps one thought line that runs past the 34-column box. It was over
before this session (35 columns) and the Dianna spelling fix pushed it to 36;
either way it clips on screen, so it is re-worded to fit.

Usage: fix_dup_tails.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BOX = 34
CLOSERS = (u")", u"」")

# Over the box in japanese-era wrapping and again after the spelling fix.
REWRAP = {
    u"Milan\n(In the end, we never determined if\nthe one before us is the real Dianna\nSoreil, or an Earthling girl.)":
    u"Milan\n(In the end, we never learned if\nshe was the real Dianna Soreil\nor an Earthling girl.)",
}


def cols(s):
    return sum(2 if ord(c) > 0x7F else 1 for c in s)


def widest(t):
    return max(cols(l) for l in t.split(u"\n"))


def trim(t):
    """Return the text without its duplicated tail, or None if it has none."""
    for i, c in enumerate(t):
        if c in CLOSERS and i + 1 < len(t):
            head, tail = t[:i + 1], t[i + 1:]
            if tail and head.endswith(tail):
                return head
    return None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    total = 0
    for ri, (hdr, data) in enumerate(live):
        d = bytearray(data)
        touched = 0
        pos = 0
        while pos < len(d):
            z = bytes(d).find(b"\x00", pos)
            if z < 0:
                break
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            field = bytes(d[pos:z])
            if not field:
                pos = k
                continue
            try:
                text = field.decode("cp932")
            except UnicodeDecodeError:
                pos = k
                continue
            new = REWRAP.get(text) or trim(text)
            if not new or new == text:
                pos = k
                continue
            nb = new.encode("cp932")
            slot = k - pos - 1
            assert len(nb) <= slot, "rec%d needs %d, slot %d" % (ri, len(nb), slot)
            print("   rec%-4d %r" % (ri, text.replace(u"\n", u"/")))
            print("        -> %r  (%d cols)" % (new.replace(u"\n", u"/"), widest(new)))
            d[pos:k] = nb + b"\x00" * (k - pos - len(nb))
            touched += 1
            pos = k
        if not touched:
            continue
        total += touched
        if not write:
            continue
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0

    print("\n%d field(s) repaired" % total)
    if write and total:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
