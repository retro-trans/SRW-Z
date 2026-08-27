# -*- coding: utf-8 -*-
"""Normalise every spelling of レーベン to Lowen in STAGE.BIN.

Reported from a screenshot 2026-08-27: "here it's still Reben".

The character is Chimera's レーベン・ゲネラール - Loewen General, German Loewen
"lion", which is why he calls himself the young lion of the Chimera and pilots
the Chaos Leo. The SRW wiki spells him Loewen with the umlaut; our font is
half-width ASCII with no umlaut, and the build already uses "Lowen" 1017 times,
so Lowen is the form everything is normalised to.

ELEVEN spellings of one character were in the shipped build:

    Lowen  1017   <- correct              Raven     3
    Loewen   50                           Raben     2
    Reeben   13                           Raeven    2
    Reben     8                           Leben     1
    Reuben    6                           Lane      1
    Reven     6

Every match is conditioned on the row's JAPANESE containing レーベン, resolved
through the row's own pointer - "Raven", "Leben" and "Lane" are ordinary words
and could not be renamed safely otherwise.

Every variant is 5 or 6 characters against Lowen's 5, so all but one shrink or
stay put and go back into their own slot. "Lane" is the single one that grows;
it takes the append-and-repoint path if it no longer fits, the same mechanism as
fix_truncated_rows.

Usage: fix_lowen.py <iso> [--write]
"""
import hashlib
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3
GOOD = "Lowen"
JP = u"レーベン"          # レーベン
# longest first, so Reeven cannot be half-matched by Reven
VARIANTS = ["Loewen", "Reeben", "Reuben", "Raeven", "Reeven",
            "Reben", "Reven", "Raven", "Raben", "Leben", "Lane"]


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())
    jpb = JP.encode("cp932")

    edited, inplace, reloc, bad, tally = {}, 0, 0, [], {}
    for idx in range(len(items)):
        e, j = items[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        eb = bytearray(e)
        jb = bytes(j)
        if jpb not in jb:
            continue
        ptr = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in ptr:
                ptr[ve] = vj
        touched = False
        for off in sorted(ptr, reverse=True):
            jo = ptr[off]
            zj = jb.find(b"\x00", jo)
            if zj <= jo or jpb not in jb[jo:zj]:
                continue
            z = bytes(eb).find(b"\x00", off)
            if z <= off:
                continue
            try:
                s = bytes(eb[off:z]).decode("cp932")
            except Exception:
                continue
            new = s
            for v in VARIANTS:
                n = len(re.findall(r"\b%s\b" % v, new))
                if n:
                    new = re.sub(r"\b%s\b" % v, GOOD, new)
                    tally[v] = tally.get(v, 0) + n
            if new == s:
                continue
            body = new.split("\n")[1:]
            if len(body) > MAXLINES or any(cols(b) > WIDTH for b in body):
                # only refuse if WE made it too wide; a row already over-width
                # in the shipped image is a fault this pass does not touch
                ob = s.split("\n")[1:]
                if len(body) > len(ob) or max([cols(b) for b in body] or [0]) > \
                        max([cols(b) for b in ob] or [0]):
                    bad.append((idx, off, "would not fit: %r" % new[:40]))
                    for v in VARIANTS:
                        n = len(re.findall(r"\b%s\b" % v, s))
                        if n:
                            tally[v] -= n
                    continue
            nb = new.encode("cp932")
            k = z
            while k < len(eb) and eb[k] == 0:
                k += 1
            if len(nb) < k - off:
                eb[off:k] = nb + b"\x00" * (k - off - len(nb))
                inplace += 1
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op = struct.pack("<I", BASE + off)
                npp = struct.pack("<I", BASE + new_off)
                cnt, q = 0, 0
                while True:
                    q = eb.find(op, q)
                    if q < 0:
                        break
                    if q % 4 == 0:
                        eb[q:q + 4] = npp
                        cnt += 1
                        q += 4
                    else:
                        q += 1
                if cnt < 1:
                    del eb[new_off:]
                    bad.append((idx, off, "no pointer to repoint"))
                    continue
                for y in range(off, k):
                    eb[y] = 0
                reloc += 1
            touched = True
        if touched:
            edited[idx] = bytes(eb)

    print("renamed to %s:" % GOOD)
    for v in VARIANTS:
        if tally.get(v):
            print("   %-8s %d" % (v, tally[v]))
    print("rows: %d in place, %d relocated | rejected %d" % (inplace, reloc, len(bad)))
    for b in bad[:8]:
        print("   REJECT rec%-4d %#08x %s" % b)
    print("records to rebuild: %d" % len(edited))
    if not write or not edited:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return

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
