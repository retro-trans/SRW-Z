# -*- coding: utf-8 -*-
"""Three lines in the Shinn/Kamille argument that say the wrong thing.

A player reported stage 35's translation as poor and sent a back-log capture.
He was right, and I had been wrong: asked to retranslate the stage I read all
483 rows, judged the prose sound, and corrected only names. The prose needed
checking too.

  row 353  「フォウの事だけ…」 + the war clause
           was "It's not about Four…There's no way those fighting a war can be
           in the right!"
           Two errors in one line. だけ - "only" - was dropped, which inverts
           it: Kamille is saying Four is not the WHOLE of it, not brushing her
           aside, and he says this one line after Shinn threw her in his face.
           And 俺達 is "we". Rendering it "those" puts him outside his own
           accusation, when the point is that he is inside it - he has just
           said he knows full well what he did was wrong.

  row 347  「議長だって、俺の事を…」
           was "Even the Chairman said about me..." - not a sentence. Row 336
           already fixes the reading: 「デュランダル議長は俺の事、わかって
           くれましたよ」 is "Chairman Durandal understood me."

  row 351  「お前だってフォウを…」
           だって is "too" - Shinn is drawing a parallel between what Kamille
           did for Four and what he did for Stella. Without it the accusation
           has no hinge.

Found by sweeping rec61 for japanese qualifiers with no english counterpart
(だけ, しか, ばかり, まだ, もう, こそ) and then reading the scene. The sweep
returned 22 candidates of which 19 were false positives - だけど is "but",
しかし is "however" - so the reading, not the sweep, is what caught 347.

Usage: fix_stage35_lines.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BOX, MAXLINES = 34, 3

FIXES = {
    u"Shinn\nSo you're saying I'm wrong!?\nEven the Chairman said about me...":
    u"Shinn\nSo you're saying I'm wrong!?\nEven the Chairman understood me...",

    u"Shinn\nThen what about you!?\nYou tried to save Four...\nan enemy, didn't you!?":
    u"Shinn\nThen what about you!? You tried\nto save Four too... an enemy,\ndidn't you!?",

    u"Kamille\nIt's not about Four…There's\nno way those fighting a\nwar can be in the right!":
    u"Kamille\nIt's not just Four… There's no\nway we're in the right, fighting\na war like this!",
}


def cols(s):
    return sum(2 if ord(c) > 0x7F else 1 for c in s)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    seen, total = set(), 0
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
            new = FIXES.get(text)
            if not new:
                pos = k
                continue
            seen.add(text)
            nb = new.encode("cp932")
            slot = k - pos - 1
            body = new.split(u"\n")[1:]
            assert len(nb) <= slot, "rec%d needs %d, slot %d" % (ri, len(nb), slot)
            assert max(cols(l) for l in body) <= BOX, "rec%d over the box" % ri
            assert len(body) <= MAXLINES, "rec%d over 3 lines" % ri
            print("   rec%-4d %r" % (ri, text.replace(u"\n", u"/")))
            print("        -> %r  (%d cols, %d lines, %d/%d bytes)"
                  % (new.replace(u"\n", u"/"), max(cols(l) for l in body),
                     len(body), len(nb), slot))
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

    for miss in set(FIXES) - seen:
        print("   NOT FOUND: %r" % miss.replace(u"\n", u"/"))
    print("\n%d line(s) fixed" % total)
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
    return 1 if set(FIXES) - seen else 0


if __name__ == "__main__":
    raise SystemExit(main())
