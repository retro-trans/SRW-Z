# -*- coding: utf-8 -*-
"""Unescape LITERAL backslash-n across ALL 205 STAGE records.

tools/fix_literal_nl.py iterates analysis/review/rec*.json, so it only ever saw
rec109-150 and reported 0 while 163 occurrences sat in the image - 134 of them
in rec104/107/136, which have no export at all. Those render to the player as
the characters \\n inside the dialogue box.

Unescaping ADDS a display line, which pushes 58 of these rows past the 3-line
limit, so the body is rejoined and re-wrapped to 34 columns rather than
substituted in place. Width counts fullwidth as 2 and expands placeholders.

Length never grows: a literal backslash-n is 2 bytes and becomes at most 1, and
re-wrapping only trades a space for a newline. The row is rewritten in its own
slot and the slack re-padded with NULs, so every pointer stays valid.

Usage: fix_literal_nl_global.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE
from fix_literal_nl import ecols, wrap, MAXLINES, O, C, TARGET

KAGI = u"「"
NUL = b"\x00"


def fix_record(data):
    """Return (new_bytes, fixed, skipped). Length preserved exactly."""
    buf = bytearray(data)
    fixed, skipped = 0, []
    i, n = 0, len(buf)
    while i < n:
        j = buf.find(NUL, i)
        if j == -1:
            j = n
        seg = bytes(buf[i:j])
        if len(seg) > 4:
            try:
                cur = seg.decode("cp932")
            except Exception:
                i = j + 1
                continue
            if TARGET in cur and KAGI in cur:
                lines = cur.split("\n")
                if len(lines) < 2:
                    skipped.append((i, "no speaker line"))
                else:
                    body = " ".join(l.strip() for l in lines[1:])
                    body = body.replace(TARGET, " ")
                    while "  " in body:
                        body = body.replace("  ", " ")
                    out = wrap(body.strip())
                    if len(out) > MAXLINES:
                        skipped.append((i, "%d lines after rewrap" % len(out)))
                    elif any(l.count(O) != l.count(C) for l in out):
                        skipped.append((i, "link split"))
                    else:
                        new = "\n".join([lines[0]] + out)
                        enc = new.encode("cp932")
                        if len(enc) <= len(seg):
                            buf[i:j] = enc + NUL * (len(seg) - len(enc))
                            fixed += 1
                        else:
                            skipped.append((i, "grew: %d > %d"
                                            % (len(enc), len(seg))))
        i = j + 1
    return bytes(buf), fixed, skipped


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, per, total, allskip = {}, {}, 0, []
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        new, fixed, skipped = fix_record(data)
        allskip += [(idx,) + s for s in skipped]
        if fixed:
            edited[idx] = new
            per[idx] = fixed
            total += fixed

    print("rows unescaped: %d in %d records" % (total, len(edited)))
    for idx in sorted(per):
        print("   rec%-4d %d" % (idx, per[idx]))
    if allskip:
        print("SKIPPED %d:" % len(allskip))
        for s in allskip[:10]:
            print("   rec%-4d off=%-7d %s" % s)
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
