# -*- coding: utf-8 -*-
"""Revert a RANGE of one STAGE record's rows to japanese, for bisecting inside it.

revert_records.py narrows a crash to a record. This narrows it inside one, so a
205-row scene takes ~8 playthroughs instead of 205.

Rows are numbered in SCRIPT ORDER - by pointer-table word position, the same
order export_proofread.py uses - because that is the order the scene plays, and
a crash "right after line N" is a statement about script order, not about where
the bytes happen to sit.

The japanese text is written into OUR field, in place, NUL-padded to the same
extent. No pointer moves and no offset changes, so the only variable is the
text itself. Japanese is usually shorter in bytes than its english (2 bytes per
kana against 1 per ASCII letter), but not always - a row whose japanese does not
fit is REPORTED AND SKIPPED rather than truncated, so a bisect is never silently
wrong about what it tested.

    revert_fields.py <iso> 79 0 102      revert the first half
    revert_fields.py <iso> 79 102 205    revert the second half

Usage: revert_fields.py <iso> <record> <from> <to> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
JP_ISO = "iso/srwz.bin"


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def rows_in_script_order(eb, jb):
    """[(english offset, japanese offset)] ordered by pointer word position."""
    seen, out = set(), []
    for p in range(0, min(len(eb), len(jb)) - 4, 4):
        ve = struct.unpack_from("<I", eb, p)[0] - BASE
        vj = struct.unpack_from("<I", jb, p)[0] - BASE
        if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in seen:
            seen.add(ve)
            out.append((p, ve, vj))
    out.sort()
    return [(ve, vj) for _p, ve, vj in out]


def text_at(b, o):
    z = bytes(b).find(b"\x00", o)
    if z < 0 or z <= o:
        return None, None
    k = z
    while k < len(b) and b[k] == 0:
        k += 1
    return bytes(b[o:z]), k - o - 1          # text, slot


def main():
    iso, rec = sys.argv[1], int(sys.argv[2])
    lo, hi = int(sys.argv[3]), int(sys.argv[4])
    write = "--write" in sys.argv
    blank = "--blank" in sys.argv

    jp = [(h, d) for h, d in banlz.decompress_all(load(JP_ISO))
          if isinstance(h, int) and d is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    hdr, data = live[rec]
    d = bytearray(data)
    jb = bytes(jp[rec][1])

    rows = rows_in_script_order(bytes(d), jb)
    print("rec%d: %d rows in script order; reverting [%d, %d)"
          % (rec, len(rows), lo, hi))

    done = skipped = 0
    for i in range(max(0, lo), min(hi, len(rows))):
        eo, jo = rows[i]
        et, slot = text_at(d, eo)
        jt, _js = text_at(jb, jo)
        if et is None or jt is None or et == jt:
            continue
        # A 4-byte word anywhere in the record can look like a pointer, so this
        # list contains false rows whose "text" is actually bytecode. rec79 has
        # eight of them pointing into 0x0220..0x0288. Overwriting those would
        # corrupt the scenario, and a bisect that corrupts what it is measuring
        # answers the wrong question. Text never contains control bytes.
        if any(c < 0x20 and c != 0x0A for c in et):
            continue
        if any(c < 0x20 and c != 0x0A for c in jt):
            continue
        if blank:
            # A short ASCII stand-in rather than the japanese. Reverting to
            # japanese makes the record compress LARGER - kana are two bytes
            # and compress worse than our ASCII - so a half-revert overflows
            # the slot, nothing is written, and chdman will happily build an
            # unmodified image that looks like a valid test. A stand-in shrinks
            # the record instead, so the bisect can always be built, and it
            # answers the same question: is the fault in THIS row's text?
            head = et.split(b"\n")[0]
            jt = head + b"\n\x81\x75.\x81\x76" if b"\x81\x75" in et else head
        if len(jt) > slot:
            print("   row %-4d SKIPPED: replacement needs %d, slot %d"
                  % (i, len(jt), slot))
            skipped += 1
            continue
        d[eo:eo + slot + 1] = jt + b"\x00" * (slot + 1 - len(jt))
        done += 1

    print("\n%d row(s) reverted, %d skipped" % (done, skipped))
    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return 1 if skipped else 0

    nxt = min([h for h in heads if h > hdr] or [len(raw)])
    blob = banlz.compress_record(bytes(d))
    if len(blob) > nxt - hdr:
        blob = banlz.compress_record_optimal(bytes(d))
    assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % rec
    raw[hdr:hdr + len(blob)] = blob
    for x in range(hdr + len(blob), nxt):
        raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
