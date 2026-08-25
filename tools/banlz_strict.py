# -*- coding: utf-8 -*-
"""Decode banlz streams the way the GAME does, and flag what our decoder hides.

banlz.decompress_stream CLAMPS a back-reference that would overrun the declared
output size:

    if len(out) + ln > total:
        ln = total - len(out)

The game does not. Its copy loop (0x1C6EA0) just counts down and stores:

    001C6EA0  addu  a3, t1, a2
    001C6EA4  lbu   a3, 0(a3)
    001C6EA8  addiu t2, t2, -0x1
    001C6EAC  sb    a3, 0(a2)
    001C6EB0  addiu a2, a2, 0x1
    001C6EB4  bne   t2, zero, 0x001C6EA0

so an over-long length writes past the buffer and, with a large count, wedges -
music keeps playing while the screen freezes. Because our decoder clamps, a
round-trip of such a record still passes, which is how this shipped.

verify(data, i, total) returns a list of problems instead of hiding them.

Usage: banlz_strict.py            audit every rebuilt file in the ISO
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz


def verify(src, i, total):
    """Decode strictly; return (out, problems)."""
    out = bytearray()
    problems = []
    n = len(src)
    while len(out) < total:
        if i >= n:
            problems.append(("input exhausted", len(out), total))
            break
        T = src[i]; i += 1
        lit = T & 0xF
        if lit == 0:
            lit, i = banlz._varint(src, i)
        nref = T >> 4
        if nref == 0:
            nref, i = banlz._varint(src, i)
        out += src[i:i + lit]
        i += lit
        if len(out) >= total:
            break
        for _ in range(nref):
            if i >= n:
                problems.append(("ref past input", len(out), total))
                break
            R = src[i]; i += 1
            d = R & 0xF
            if (d & 1) == 0:
                while True:
                    d = (d << 7) | src[i]
                    i += 1
                    if d & 1:
                        break
            dist = d >> 1
            ln = R >> 4
            if ln == 0:
                ln, i = banlz._varint(src, i)
            ln += 1
            pos = len(out) - dist - 1
            if pos < 0:
                problems.append(("negative distance", len(out), dist))
                return bytes(out), problems
            if len(out) + ln > total:
                # THE GAME WOULD OVERRUN HERE
                problems.append(("ref overruns output by %d"
                                 % (len(out) + ln - total), len(out), ln))
                ln = total - len(out)
            for k in range(ln):
                out.append(out[pos + k])
            if len(out) >= total:
                break
    return bytes(out), problems


def audit_file(data, label, limit=None):
    off = 0
    idx = 0
    bad = 0
    first = []
    while off < len(data) - 8 and (limit is None or idx < limit):
        try:
            total, flags, at = banlz.parse_header(data, off)
        except Exception:
            break
        try:
            out, probs = verify(data, at, total)
        except Exception as e:
            probs = [("exception: %s" % str(e)[:40], 0, 0)]
            out = b""
        try:
            _, end = banlz.decompress_stream(data, at, total)
        except Exception:
            break
        if probs:
            bad += 1
            if len(first) < 8:
                first.append((idx, probs[0]))
        if end <= off:
            break
        off = end
        idx += 1
    print("%-22s %4d records | records the GAME would overrun: %d"
          % (label, idx, bad))
    for i, p in first:
        print("     rec %-4d %s (at out=%d, len=%d)" % (i, p[0], p[1], p[2]))
    return bad


def main():
    WORK = r"E:\Projects\SRW Z\_work"
    ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
    # (name, lba, sectors, record count) - COMPDATA is ONE record, not a stream
    FILES = [("MTVZKNPT", 1573457, 136, None), ("MTVZKNRT", 1824000, 97, None),
             ("MTVZKNKW", 1823200, 16, None), ("COMPDATA", 1823000, 74, 1),
             ("STAGE", 1651029, 1910, 205), ("MTV_PROS", 1573437, 5, 14)]
    f = open(ISO, "rb")
    tot = 0
    for name, lba, sec, lim in FILES:
        f.seek(lba * 2048)
        tot += audit_file(f.read(sec * 2048), name, lim)
    f.close()
    print("\nfiles with at least one overrunning record: %s" % ("YES" if tot else "no"))


if __name__ == "__main__":
    main()
