# -*- coding: utf-8 -*-
"""Re-apply analysis/english_script.json to a disc image.

This is the other half of export_english_script.py, and together they are what
makes the project forkable: the translation lives in the image, the image cannot
be published, so the English is exported as our own work product and re-applied
to an image the user dumps themselves.

WHAT IT CAN AND CANNOT DO - read this before relying on it:

  * Rows are keyed by (record, byte offset). Those offsets describe the layout
    of OUR patched image. Applying to a build in that lineage works.
  * Applying to a VIRGIN japanese image does NOT fully work. Rows that grew past
    their original slot were relocated to the end of the record and their
    pointers rewritten (see "option 3" in docs/TECHNICAL.md), so their offsets
    do not exist in an unpatched image. Those rows are reported as out-of-range
    and skipped rather than written to a wrong address.

So this restores the translation onto a build, and is a complete human-readable
record of the translation either way. It is not a one-click "translate a fresh
ISO" button, and pretending otherwise would waste somebody's afternoon.

Every write is length-checked against the slot and the slack is NUL-padded, so
no offset inside a record moves. Verify with tools/verify_pointers.py after.

Usage: apply_english_script.py <iso> <english_script.json> [--write]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

NUL = b"\x00"


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso, src = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    rows = json.load(io.open(src, encoding="utf-8"))["rows"]

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, same, wrote, oor, toolong = {}, 0, 0, 0, 0
    for r in rows:
        idx, off, en = r["rec"], r["off"], r["en"]
        if idx >= len(items) or items[idx][1] is None:
            oor += 1
            continue
        buf = bytearray(edited.get(idx, items[idx][1]))
        if off >= len(buf):
            oor += 1
            continue
        e = buf.find(NUL, off)
        if e == -1:
            oor += 1
            continue
        k = e
        while k < len(buf) and buf[k] == 0:
            k += 1
        cur = bytes(buf[off:e])
        try:
            nb = en.encode("cp932")
        except Exception:
            toolong += 1
            continue
        if nb == cur:
            same += 1
            continue
        if len(nb) > k - off:
            toolong += 1
            continue
        buf[off:k] = nb + NUL * (k - off - len(nb))
        edited[idx] = bytes(buf)
        wrote += 1

    print("rows in export        : %d" % len(rows))
    print("  already identical   : %d" % same)
    print("  would write         : %d" % wrote)
    print("  offset out of range : %d  (relocated rows - see the docstring)" % oor)
    print("  will not fit slot   : %d" % toolong)
    print("  records touched     : %d" % len(edited))
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
    print("written")


if __name__ == "__main__":
    main()
