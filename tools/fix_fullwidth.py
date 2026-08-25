# -*- coding: utf-8 -*-
"""Fullwidth punctuation -> ASCII, in ENGLISH DIALOGUE only.

REWRITTEN 2026-08-24. The previous version corrupted 58 records and shipped as
v0.8.72, which froze when loading a save. It did two fatal things:

    text = bytes(data).decode("cp932", "ignore")   # DROPS binary bytes
    blob = "\\x00".join(parts).encode(...)          # shifts everything LEFT
    buf[:len(blob)] = blob

Rejoining the record pulled every byte after each shortened string leftwards
while the pointer table kept the old offsets. Record LENGTH was unchanged (the
tail was NUL-padded), so every length check still passed.

This version rewrites each NUL-terminated string IN PLACE and re-pads the slack
with NULs inside that same string, so every offset in the record is preserved
exactly. Verify with tools/verify_pointers.py before building.

In menu-drawn rows ASCII 0x2E-0x3D are CONTROL CODES, so fullwidth is correct
there; only rows carrying the quote mark or a fullwidth paren are touched, and
only if they contain Latin letters.

Usage: fix_fullwidth.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

MAP = {u"．": ".", u"！": "!", u"？": "?", u"，": ","}
KAGI, PAREN = u"「", u"（"
NUL = b"\x00"


def fix_record(data):
    """Return (new_bytes, rows, chars, samples). Length preserved exactly."""
    buf = bytearray(data)
    rows = chars = 0
    samples = []
    i, n = 0, len(buf)
    while i < n:
        j = buf.find(NUL, i)
        if j == -1:
            j = n
        seg = bytes(buf[i:j])
        if seg:
            try:
                s = seg.decode("cp932")
            except Exception:
                i = j + 1
                continue
            if (KAGI in s or PAREN in s) and any(
                    ("a" <= c <= "z") or ("A" <= c <= "Z") for c in s):
                new = s
                for fw, asc in MAP.items():
                    new = new.replace(fw, asc)
                if new != s:
                    enc = new.encode("cp932")
                    if len(enc) <= len(seg):
                        if len(samples) < 4:
                            samples.append((s.replace("\n", " | ")[:54],
                                            new.replace("\n", " | ")[:54]))
                        chars += sum(s.count(k) for k in MAP)
                        buf[i:j] = enc + NUL * (len(seg) - len(enc))
                        rows += 1
        i = j + 1
    return bytes(buf), rows, chars, samples


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, rows, chars, shown = {}, 0, 0, []
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        new, r, c, samples = fix_record(data)
        if r:
            edited[idx] = new
            rows += r
            chars += c
            if len(shown) < 4 and samples:
                shown.append((idx,) + samples[0])

    print("dialogue lines fixed: %d  (%d characters) in %d records"
          % (rows, chars, len(edited)))
    for idx, a, b in shown:
        print("   rec%-4d %s" % (idx, a))
        print("        -> %s" % b)
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


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


if __name__ == "__main__":
    main()
