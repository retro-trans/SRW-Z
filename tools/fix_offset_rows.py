# -*- coding: utf-8 -*-
u"""Rewrite a STAGE row addressed by OFFSET, relocating it if it outgrows its slot.

apply_lines_relocating.py does this by row KEY, but keys only exist for rows the
proofread export produced - and the export defines a row by the japanese \u300c
([[dialogue-identified-by-japanese-bracket]]). A parenthesised THOUGHT has no
\u300c, so it has no key, and no tool could address it at all.

That is how this was found. A player reported Kazami's line rendering as

    Kazami
    (First demons and...)

against \u98a8\u898b\uff08\u307e\u305a\u306f\u9b3c\u3068\u5815\u5929\u7fc5\u304b\u2026\uff09 - the SECOND noun, \u5815\u5929\u7fc5 the Shadow
Angels, is simply gone. The slot holds 31 bytes and the honest line needs 50,
which is presumably why it was cut; but the budget is not real. STAGE rows are
addressed by absolute pointers (BASE 0x7566F0), so a row that outgrows its slot
is appended past the end of the record and its pointer rewritten - the same
mechanism fix_truncated_rows.py uses.

Guards: the row must decode, at least one 4-aligned pointer to it must be found
before anything moves, and the record set must be unchanged after recompression.

Usage: fix_offset_rows.py <iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
BASE = 0x7566F0

# (rec, offset) -> the full field, speaker line included
FIX = {
    (112, 0x192e0): u'Kazami\n(First the demons and the Shadow\nAngels...)',
}


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    touched, inplace, moved = {}, 0, 0
    for (rec, off), new in sorted(FIX.items()):
        d = live[rec][1]
        z = bytes(d).find(b"\x00", off)
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        old = bytes(d[off:z]).decode("cp932")
        nb = new.encode("cp932")
        print("rec%d %#x: %r" % (rec, off, old.replace("\n", " | ")))
        print("        -> %r  (%d B, slot %d)"
              % (new.replace("\n", " | "), len(nb), k - off - 1))
        if len(nb) < k - off:
            d[off:k] = nb + b"\x00" * (k - off - len(nb))
            inplace += 1
        else:
            dst = len(d)
            op = struct.pack("<I", BASE + off)
            npn = struct.pack("<I", BASE + dst)
            cnt, j = 0, 0
            while True:
                j = bytes(d).find(op, j)
                if j < 0:
                    break
                if j % 4 == 0:
                    d[j:j + 4] = npn
                    cnt += 1
                    j += 4
                else:
                    j += 1
            if cnt < 1:
                print("        REFUSED: no 4-aligned pointer to repoint")
                f.close()
                return 1
            d += nb + b"\x00"
            for x in range(off, z):
                d[x] = 0
            print("        relocated to %#x, %d pointer(s) rewritten" % (dst, cnt))
            moved += 1
        touched[rec] = True
    print("rows: %d in place, %d relocated" % (inplace, moved))
    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return 0
    for rec in sorted(touched):
        h = live[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(bytes(live[rec][1]))
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(bytes(live[rec][1]))
        assert len(blob) <= nxt - h, "rec%d over slot" % rec
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
