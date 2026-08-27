# -*- coding: utf-8 -*-
"""Restore dialogue rows that were cut short to fit their slot.

Reported from a backlog screenshot 2026-08-26: Zushi's line rendered

    Zushi
    "As you

The stored row was `Zushi\\n"As you`. The Japanese `頭翅\\n「御意…」` fits a 16-byte
slot; the English does not, so whoever fitted it swapped the 2-byte kagi for a
1-byte ASCII quote and then cut the sentence off. 32 rows are damaged this way.

scan_visible_defects.py could never see it: each row is one line, under 34
columns, has no literal escape and no Japanese left. What is wrong is the
QUOTING, which is what tools/scan_broken_quotes.py now checks.

The budget is not real. STAGE rows are addressed by absolute pointers
(BASE 0x7566F0) exactly like the COMPDATA pool, so a row that outgrows its slot
is appended to the end of the record and its pointer rewritten - the mechanism
apply_fixes.py already uses, and the reason 133 rows in rec48 live past the
Japanese high-water mark.

Two rows are left deliberately unclosed: rec185's Rand and Denzel lines have no
closing bracket in the JAPANESE either, so mirroring the source is correct.

Usage: fix_truncated_rows.py <iso> [--write]
"""
import hashlib
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
O, C = u"「", u"」"

# (record, offset-as-shipped) -> replacement. Offsets come from
# tools/trunc_report.py, which resolves each row through its pointer.
FIX = {
    (6,   0x008ba0): u"Kappei\n「Kazuki...」",
    (26,  0x00d980): u"Keiko\n「Kappei...」",
    (37,  0x00b280): u"Keiko\n「Kappei...」",
    (37,  0x00f780): u"Kappei\n「Kazuki...」",
    (45,  0x012630): u"Gengoro\n「Rumors?」",
    (48,  0x013670): u"Zushi\n「As you wish...」",
    (62,  0x007380): u"Umee\n「There are too many, so we split\nthem between the holds of\nBial II and III.」",
    (62,  0x00adf0): u"Kappei\n「A dream?」",
    (64,  0x005530): u"Kouji\n「A sin...?」",
    (64,  0x005e00): u"???\n「If the Genesis Machine Gran\nSigma is fully completed, Lanbias'\npollution could be stopped...」",
    (64,  0x0063f0): u"Sandman\n「Once the Gran Sigma is complete,\nas a Genesis Machine it can wield\nthe power to create stars...」",
    (72,  0x012396): u"President\n「What...?」",
    (101, 0x017b22): u"President\n「What...?」",
    (104, 0x010ef0): u"Keiko\n「Kappei...」",
    (104, 0x014340): u"Ichitaro\n「What...」",
    (107, 0x024920): u"Kappei\n「Kazuki...」",
    (117, 0x015850): u"Shishi\n「Reika...」",
    (120, 0x013bb0): u"Sandman\n「Gran Sigma... the time has come\nto use your power again. But I\nwill not repeat my mistakes!」",
    (127, 0x022040): u"Reika\n「A dream...?」",
    (128, 0x015230): u"Shishi\n「Reika...」",
    (131, 0x020540): u"Sandman\n「Gran Sigma... the time has come\nto use your power again. But I\nwill not repeat my mistakes!」",
    (132, 0x015450): u"Kazuki\n「Kappei...」",
    (136, 0x0182a0): u"Garrod\n「Mistakes won't repeat! I...we\nwill!!」",
    # speaker shipped as "Dianna"; the japanese speaker is ギンガナム.
    # These are Ghingnham taunting Dianna, so the wrong name inverted the scene.
    (137, 0x0058b0): u"Ghingnham\n「If Dianna gave me that pride,\nthen Dianna's who took it away!」",
    (137, 0x005950): u"Ghingnham\n「You, prattling about doing this\nfor Dianna, let alone the world,\nyou could never defeat me!」",
    (137, 0x006090): u"Ghingnham\n「Hahahahaha!\nHahahahahahahahahaha!\nFarewell, Dianna!!」",
    (143, 0x018240): u"Kei\n「Captain...!」",
    (145, 0x0181c0): u"Kappei\n「Kazuki...」",
    (148, 0x019db0): u"Kei\n「Captain...!」",
    (150, 0x018ce0): u"Kappei\n「Kazuki...」",
    # unclosed in the japanese too - mirror the source, fix only the quote mark
    (185, 0x008f30): u"Rand\n「Heh...too easy, makes me yawn.",
    (185, 0x00abb0): u"Denzel\n「With that ability screen open,\npress Select, then move to the\nterm you want to",
}
UNCLOSED = {(185, 0x008f30), (185, 0x00abb0)}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return cols(s)


def validate(key, old, new):
    if "\n" not in new:
        return "no speaker line"
    body = new.split("\n")[1:]
    if len(body) > MAXLINES:
        return "%d body lines" % len(body)
    for b in body:
        if ecols(b) > WIDTH:
            return "line %d cols: %r" % (ecols(b), b)
    if key not in UNCLOSED and new.count(O) != new.count(C):
        return "unbalanced kagi"
    if '"' in new:
        return "still contains an ascii quote"
    try:
        new.encode("cp932")
    except UnicodeEncodeError as ex:
        return "not cp932: %r" % ex.object[ex.start:ex.end]
    return None


CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "analysis", "_lzcache")


def _compress(args):
    """Fast coder first - these records gain a few dozen bytes at most, so the
    fast stream still fits the slot and the optimal parser (minutes per record)
    is only needed if it does not.

    Results are CACHED on disk keyed by the plain record's sha1. Compressing 24
    records takes longer than a background job is allowed to live, and two runs
    were cut off partway with nothing written; with the cache each run resumes
    where the last stopped instead of redoing the work."""
    n, plain, room = args
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    key = os.path.join(CACHE, "%s.lz" % hashlib.sha1(plain).hexdigest())
    if os.path.exists(key):
        blob = open(key, "rb").read()
        if len(blob) <= room:
            return n, blob, True
    blob = banlz.compress_record(plain)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(plain)
    open(key, "wb").write(blob)
    return n, blob, False


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))

    edited, inplace, reloc, bad = {}, 0, 0, []
    for (n, off), new in sorted(FIX.items()):
        eb = bytearray(edited.get(n, items[n][1]))
        e = off
        while e < len(eb) and eb[e] != 0:
            e += 1
        k = e
        while k < len(eb) and eb[k] == 0:
            k += 1
        try:
            old = bytes(eb[off:e]).decode("cp932")
        except UnicodeDecodeError:
            bad.append((n, off, "undecodable"))
            continue
        why = validate((n, off), old, new)
        if why:
            bad.append((n, off, why))
            continue
        if old.split("\n")[0] != new.split("\n")[0]:
            print("   rec%-4d %#08x speaker %r -> %r"
                  % (n, off, old.split("\n")[0], new.split("\n")[0]))
        nb = new.encode("cp932")
        if len(nb) < k - off:
            eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            inplace += 1
        else:
            new_off = len(eb)
            eb += nb + b"\x00"
            op = struct.pack("<I", BASE + off)
            np_ = struct.pack("<I", BASE + new_off)
            cnt, j = 0, 0
            while True:
                j = eb.find(op, j)
                if j < 0:
                    break
                if j % 4 == 0:
                    eb[j:j + 4] = np_
                    cnt += 1
                    j += 4
                else:
                    j += 1
            if cnt < 1:
                del eb[new_off:]
                bad.append((n, off, "no pointer to repoint"))
                continue
            for x in range(off, k):
                eb[x] = 0
            reloc += 1
        edited[n] = bytes(eb)

    print("rows fixed: %d in place, %d relocated | rejected %d"
          % (inplace, reloc, len(bad)))
    for b in bad:
        print("   REJECT rec%-4d %#08x %s" % b)
    print("records to rebuild: %d" % len(edited))
    if not write or not edited or bad:
        if bad:
            print("\nREFUSING to write while any row is rejected")
        elif not write:
            print("\n(dry run - pass --write to apply)")
        return

    jobs = []
    for n, plain in edited.items():
        hdr = items[n][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        jobs.append((n, plain, nxt - hdr))
    packed = {}
    for j in jobs:
        n, blob, hit = _compress(j)
        packed[n] = blob
        print("   rec%-4d %d bytes (slot %d)%s"
              % (n, len(blob), j[2], " [cached]" if hit else ""))
        sys.stdout.flush()
    for n, plain in edited.items():
        hdr = items[n][0]
        blob = packed[n]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot (%d > %d)" % (
            n, len(blob), nxt - hdr)
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for n, plain in edited.items():
        assert bytes(chk[n][1]) == plain, "readback mismatch rec %d" % n
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")


if __name__ == "__main__":
    main()
