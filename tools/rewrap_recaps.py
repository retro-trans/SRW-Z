# -*- coding: utf-8 -*-
"""Rewrap the scenario-chart recaps to the width the box actually has.

Reported from a screenshot 2026-08-27: a recap ran off the bottom of the
Scenario Chart box.

The recaps are long prose paragraphs in STAGE.BIN, not dialogue rows - which is
why find_row never showed them (it only matches rows containing 「) and why
searching for their text in HSFC, COMPDATA and the ELF found nothing. HSFC holds
the SHORT map-select one-liners ("AEUG raids Lutetium Base"), a different thing.

The bug is the wrap width. Measured across all 210 recaps:

    japanese line counts cluster at 10-11, max 22
    english  line counts spread to 25, and 113 of 210 use MORE lines than the
             japanese they replace
    english  max line width: mean 40, but the WIDEST already reach 56

So the box is 56 columns - the japanese uses all of it and some english lines
already do - and most english was wrapped at ~38-40, wasting a third of the box
and spilling into extra lines that fall out of the bottom.

Rewrapping every recap to 56 columns:

    recaps still longer than their japanese :  113 -> 0
    recaps that grow in bytes               :        0

Nothing grows, so every one is written into its existing slot: no relocation, no
repointing, and the pointers repaired in 0.8.90 are untouched.

Only recaps are touched - a string is one only if it is >=160 bytes, contains no
「, and resolves through its pointer to a japanese string. Dialogue is never
rewrapped by this pass.

Usage: rewrap_recaps.py <iso> [--width 56] [--write]
"""
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
KAGI = u"「"
MINLEN = 160


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def rewrap(text, width):
    words = text.replace("\n", " ").split()
    out, cur = [], ""
    for w in words:
        t = (cur + " " + w) if cur else w
        if cols(t) <= width:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return "\n".join(out)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    W = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 56
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())

    edited, n, saved, skipped = {}, 0, 0, 0
    for idx in range(len(items)):
        e, j = items[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        eb = bytearray(e)
        jb = bytes(j)
        seen = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in seen:
                seen[ve] = vj
        touched = False
        for eo in sorted(seen, reverse=True):
            ze = bytes(eb).find(b"\x00", eo)
            if ze - eo < MINLEN:
                continue
            zj = jb.find(b"\x00", seen[eo])
            if zj <= seen[eo]:
                continue
            try:
                se = bytes(eb[eo:ze]).decode("cp932")
            except Exception:
                continue
            if KAGI in se:
                continue
            new = rewrap(se, W)
            if new == se:
                continue
            nb = new.encode("cp932")
            if len(nb) > ze - eo:
                skipped += 1
                continue
            k = ze
            while k < len(eb) and eb[k] == 0:
                k += 1
            eb[eo:k] = nb + b"\x00" * (k - eo - len(nb))
            saved += len([x for x in se.split("\n") if x]) - (new.count("\n") + 1)
            n += 1
            touched = True
        if touched:
            edited[idx] = bytes(eb)

    print("recaps rewrapped to %d columns: %d" % (W, n))
    print("lines saved in total          : %d" % saved)
    print("skipped (would not fit)       : %d" % skipped)
    print("records to rebuild            : %d" % len(edited))
    if not write or not edited:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return

    import hashlib
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "analysis", "_lzcache")
    if not os.path.isdir(cdir):
        os.makedirs(cdir)
    for idx, plain in edited.items():
        hdr = items[idx][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        key = os.path.join(cdir, "%s.lz" % hashlib.sha1(plain).hexdigest())
        if os.path.exists(key):
            blob = open(key, "rb").read()
        else:
            blob = banlz.compress_record(plain)
            if len(blob) > nxt - hdr:
                blob = banlz.compress_record_optimal(plain)
            open(key, "wb").write(blob)
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        print("   rec%-4d %d bytes (slot %d)" % (idx, len(blob), nxt - hdr))
        sys.stdout.flush()
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for idx, plain in edited.items():
        assert bytes(chk[idx][1]) == plain, "readback mismatch rec %d" % idx
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")


if __name__ == "__main__":
    main()
