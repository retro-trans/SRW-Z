# -*- coding: utf-8 -*-
"""The last seven player-visible defects found by scan_visible_defects.py.

Six untranslated Japanese lines and one row that cannot be re-wrapped into the
3x34 box without shortening the text.

  rec18   Loran's scream, still Japanese
  rec177-180  "This is the last bazaar", Japanese, with a Japanese speaker name
  rec203  Bright, INLINE format (name + quote on ONE line, no newline)
  rec116  35 columns; "lift-board lessons from Holland...」" is 35 on its own,
          so no re-flow fits it - the text itself has to give ("naughty"->
          "shady", drop "-board")

MUST be a real file, not a heredoc: multiprocessing on Windows re-imports the
module in every spawned worker and a heredoc has no importable path
(OSError: Invalid argument: '<stdin>'). This has now bitten this project three
times.

Every replacement is validated before it is written: encodable as cp932, fits
the existing slot, <= 3 body lines, <= 34 columns with placeholders EXPANDED.

Usage: fix_last_seven.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}

FIX = {
    (18, 3536):   u"Loran\n「Uwaaaaaahhh!!」",
    (116, 23200): u"Sara\n「Hunted a shady shop with\n$n, ate lizard with Jiron,\n"
                  u"lift lessons from Holland…」",
    (177, 3872):  u"Jiron\n「This is the last bazaar.」",
    (178, 3744):  u"Jiron\n「This is the last bazaar.」",
    (179, 3872):  u"Jiron\n「This is the last bazaar.」",
    (180, 3744):  u"Jiron\n「This is the last bazaar.」",
    (203, 9168):  u"Bright「Let's give it our all.」",
}


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited = {}
    for (idx, off), new in sorted(FIX.items()):
        buf = bytearray(edited.get(idx, items[idx][1]))
        e = buf.find(NUL, off)
        k = e
        while k < len(buf) and buf[k] == 0:
            k += 1
        old = bytes(buf[off:e]).decode("cp932", "ignore")
        nb = new.encode("cp932")
        lines = new.split("\n")
        body = lines[1:] if len(lines) > 1 else [lines[0]]
        wide = max(ecols(l) for l in body)
        assert len(nb) <= k - off, "rec%d needs %d, slot %d" % (idx, len(nb), k - off)
        assert wide <= WIDTH, "rec%d is %d columns" % (idx, wide)
        assert len(body) <= MAXLINES, "rec%d has %d body lines" % (idx, len(body))
        buf[off:k] = nb + NUL * (k - off - len(nb))
        edited[idx] = bytes(buf)
        print("  rec%-4d slot=%-3d new=%-3dB cols=%-3d" % (idx, k - off, len(nb), wide))
        print("      old: %r" % old.replace("\n", " | "))
        print("      new: %r" % new.replace("\n", " | "))

    print("\nrows fixed: %d in %d records" % (len(FIX), len(edited)))
    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return

    import multiprocessing
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close()
    pool.join()
    for idx, plain in edited.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw))
             if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written")


if __name__ == "__main__":
    main()
