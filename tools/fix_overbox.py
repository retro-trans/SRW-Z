# -*- coding: utf-8 -*-
"""Two dialogue rows wider than the box they are drawn in.

Both surfaced only after export_proofread.py stopped identifying a dialogue row
by the 「 in the ENGLISH. Roughly 500 rows use ASCII quotes or none at all, so
they had never been exported, never proofread and never width-checked.

Twelve of those newly-visible rows sit over 34 columns. Ten are not defects:
their JAPANESE is over 34 too, because they are drawn in wider panels - the
rec137 briefing box runs 38-44 columns in japanese, and the rec1/rec25
encyclopedia panels run 50. Judging a fragment against an absolute width
instead of against its own japanese is exactly what produced the wrong weapon
-name "fix" in 0.9.26, so the test here is the japanese, not a constant.

That leaves two where the japanese fits and ours does not:

  rec138  JP 26 columns, ours 38. One long line that simply needs a break.
  rec144  JP 34 columns over 3 lines, ours 36 over 2 - because the english
          DROPPED A WHOLE LINE. 「ジ・エーデル！」 is Sandman shouting The Edel's
          name, and it is missing; the row also lost its opening quote. There
          were 25 spare bytes, so this was never a budget problem.

Usage: fix_overbox.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BOX = 34

FIXES = {
    # one line, 38 columns; the japanese is 26. Just needs the break.
    u'Quattro\n"All units, disperse! Here they come!"':
    u'Quattro\n"All units, disperse!\nHere they come!"',
    # restores 「ジ・エーデル！」 and the opening quote
    u'Sandman\nI\'ll defeat you for that!\nWith the power of the hope I found!"':
    u'Sandman\n"The Edel! I\'ll defeat you for\nthat! With the power of the hope\nI found!"',
}


def cols(s):
    return sum(2 if ord(c) > 0x7F else 1 for c in s)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    seen, total = set(), 0
    for ri, (hdr, data) in enumerate(live):
        d = bytearray(data)
        touched = 0
        pos = 0
        while pos < len(d):
            z = bytes(d).find(b"\x00", pos)
            if z < 0:
                break
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            field = bytes(d[pos:z])
            if not field:
                pos = k
                continue
            try:
                text = field.decode("cp932")
            except UnicodeDecodeError:
                pos = k
                continue
            new = FIXES.get(text)
            if not new:
                pos = k
                continue
            seen.add(text)
            nb = new.encode("cp932")
            slot = k - pos - 1
            body = new.split(u"\n")[1:]
            assert len(nb) <= slot, "rec%d needs %d, slot %d" % (ri, len(nb), slot)
            assert max(cols(l) for l in body) <= BOX, "rec%d still over the box" % ri
            assert len(body) <= 3, "rec%d has more than 3 body lines" % ri
            print("   rec%-4d %r" % (ri, text.replace(u"\n", u"/")))
            print("        -> %r  (%d cols, %d lines)"
                  % (new.replace(u"\n", u"/"), max(cols(l) for l in body), len(body)))
            d[pos:k] = nb + b"\x00" * (k - pos - len(nb))
            touched += 1
            pos = k
        if not touched:
            continue
        total += touched
        if not write:
            continue
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0

    for miss in set(FIXES) - seen:
        print("   NOT FOUND: %r" % miss.replace(u"\n", u"/"))
    print("\n%d row(s) fixed" % total)
    if write and total:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
