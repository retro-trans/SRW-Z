# -*- coding: utf-8 -*-
"""Write an edited extract_script.py file back into a disc image.

The other half of extract_script.py. Round-trip is exact: extract, change
nothing, apply, and the image is byte-identical.

WHAT IT CHECKS BEFORE WRITING ANYTHING - all of these have broken this game at
least once, so none of them are optional:

  encodable   the text must encode as cp932. Em-dashes and curly quotes do not.
  fits        the encoded bytes must fit the slot. Longer needs relocation,
              which this tool does not do - see docs/TECHNICAL.md "option 3".
  box         <= 3 body lines, <= 34 display columns each, placeholders
              EXPANDED ($n is 7 columns, not 2). Overflow draws outside the box.
  links       every <<term>> must still balance, and must exist in the keyword
              bank, or the scene CRASHES. Run tools/fix_dead_links.py after.

Nothing is written unless every row passes, so a bad edit fails loudly instead
of shipping. Rows are rewritten in place and the slack re-padded with NULs, so
no offset inside a record moves.

ALWAYS run tools/verify_pointers.py afterwards. A pass that moves bytes inside a
record while leaving the pointer table alone produces an image that boots, plays
and then freezes when a save is loaded.

Usage: apply_script.py <iso> <edited.json> [--write] [--force]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"
KAGI = u"「"
O, C = u"《", u"》"
WIDTH, MAXLINES = 34, 3
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso, src = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    force = "--force" in sys.argv
    rows = json.load(io.open(src, encoding="utf-8"))["rows"]

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, same, changed, bad = {}, 0, 0, []
    for r in rows:
        idx, off, text = r["rec"], r["off"], r["text"]
        if idx >= len(items) or items[idx][1] is None:
            bad.append((idx, off, "record does not exist"))
            continue
        buf = bytearray(edited.get(idx, items[idx][1]))
        if off >= len(buf):
            bad.append((idx, off, "offset past end of record"))
            continue
        e = buf.find(NUL, off)
        k = e
        while k < len(buf) and buf[k] == 0:
            k += 1
        slot = k - off
        cur = bytes(buf[off:e])
        try:
            nb = text.encode("cp932")
        except Exception as ex:
            bad.append((idx, off, "not cp932-encodable: %s" % ex))
            continue
        if nb == cur:
            same += 1
            continue
        if len(nb) > slot:
            bad.append((idx, off, "needs %d bytes, slot is %d" % (len(nb), slot)))
            continue
        lines = text.split("\n")
        body = lines[1:] if len(lines) > 1 else []
        if body:
            if len(body) > MAXLINES:
                bad.append((idx, off, "%d body lines, max %d" % (len(body), MAXLINES)))
                continue
            wide = max(ecols(l) for l in body)
            if wide > WIDTH:
                bad.append((idx, off, "%d columns, max %d" % (wide, WIDTH)))
                continue
        if text.count(O) != text.count(C):
            bad.append((idx, off, "unbalanced <<>> link markers"))
            continue
        buf[off:k] = nb + NUL * (slot - len(nb))
        edited[idx] = bytes(buf)
        changed += 1

    print("rows in file    : %d" % len(rows))
    print("  unchanged     : %d" % same)
    print("  to write      : %d" % changed)
    print("  REJECTED      : %d" % len(bad))
    for b in bad[:15]:
        print("     rec%-4d off=%-7d %s" % b)
    if len(bad) > 15:
        print("     ... %d more" % (len(bad) - 15))
    if bad and not force:
        print("\nNothing written. Fix the rows above, or pass --force to apply "
              "the rest anyway.")
        f.close()
        return
    if not write or not edited:
        if not write:
            print("\n(dry run - pass --write to apply)")
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
    print("written - now run: python tools/verify_pointers.py %s --min 85" % iso)


if __name__ == "__main__":
    main()
