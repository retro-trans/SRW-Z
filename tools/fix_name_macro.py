# -*- coding: utf-8 -*-
"""Restore the protagonist-name macro in the victory/defeat objective lines.

THE BUG. A player reached Ep.15, opened Operation End and read:

    Defeat
      1. Ally battleship lost
      2. : shot down.

Shot who down? The line names nobody.

Byte 0x3A - ASCII ':' - is not a colon on the text path, it is the macro that
expands to the protagonist's name (Rand or Setsuko, whichever the player
chose). The japanese objective is literally ':の撃墜。' and draws as
"Setsuko shot down."

Our translation pass wrote ':' fullwidth as '：' (0x81 0x46) everywhere, for a
good reason - a stray ASCII ':' in menu text expands to the protagonist's name
in the middle of a sentence, which is how "Setsuko" once turned up inside a
help panel. But that rule is wrong for these eleven strings, because here the
expansion is the WHOLE POINT. Widening it did not escape the macro, it deleted
it: '：' is an ordinary glyph and draws as a bare colon.

So the fix is to put back the exact byte the japanese uses. That makes these
strings byte-identical to the original disc on the macro, which is the
strongest guarantee available that they behave the way the japanese does.

Eleven strings across seven records were checked against the japanese pointer
by pointer: 11 had the macro widened, 0 had it dropped, and 8 more that are
already a raw ':' were left alone. rec83's second variant was never translated
at all and is done here too, since it is the same line.

BYTE SAFETY. '：' is two bytes and ':' is one, so every string SHRINKS. The
replacement is written at the same offset and the slack is zero-filled, so the
terminator lands earlier inside the old extent and nothing after it moves. No
row pointer changes.

Usage: fix_name_macro.py <iso> [--write]
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
FW = b"\x81\x46"                       # fullwidth colon, the broken form
MACRO = b"\x3a"                        # what the japanese actually stores

# offset -> (expected english, replacement). Offsets are inside the decompressed
# record; every one was paired against its japanese counterpart by pointer.
FIX = {
 28: {0x01c7d8: (u"\uff1a shot down\uff0e",           u": shot down\uff0e"),
      0x01c810: (u"\uff1a or Toby shot down\uff0e",   u": or Toby shot down\uff0e"),
      0x01c830: (u"\uff1a or Asakim shot down\uff0e", u": or Asakim shot down\uff0e")},
 41: {0x010150: (u"\uff1a or Toby shot down\uff0e",   u": or Toby shot down\uff0e")},
 42: {0x00ed18: (u"\uff1a shot down\uff0e",           u": shot down\uff0e"),
      0x00ed50: (u"\uff1a or Asakim shot down\uff0e", u": or Asakim shot down\uff0e")},
 54: {0x016757: (u"Shoot down either \uff1a or Kamille\uff0e",
                 u"Shoot down either : or Kamille\uff0e"),
      0x015c00: (u"Shoot down \uff1a",                u"Shoot down :")},
 56: {0x0107d8: (u"\uff1a shot down\uff0e",           u": shot down\uff0e")},
 57: {0x00d948: (u"\uff1a shot down\uff0e",           u": shot down\uff0e")},
 # 0x017210 is the two-name variant; 0x017250 is the three-name one, which the
 # translation passes never reached - it is still the japanese line.
 83: {0x017210: (u"Holland or \uff1a shot down\uff0e",
                 u"Holland or : shot down．"),
      0x017250: (b'\x83z\x83\x89\x83\x93\x83h\x81E:\x81E\x83A\x83T\x83L\x83\x80\x81A\x82\xa2\x82\xb8\x82\xea\x82\xa9\x82\xcc\x8c\x82\x92\xc4\x81B',
                 u"Holland, : or Asakim shot down．")},
}


def edit(dec, table):
    b = bytearray(dec)
    done = []
    for off in sorted(table):
        want, new = table[off]
        z = b.find(b"\x00", off)
        got = bytes(b[off:z])
        exp = want if isinstance(want, bytes) else want.encode("cp932")
        if got != exp:
            raise SystemExit("rec offset %#08x holds %r, expected %r"
                             % (off, got.decode("cp932", "replace"),
                                exp.decode("cp932", "replace")))
        nb = new.encode("cp932")
        if len(nb) > len(got):
            raise SystemExit("%#08x would grow %d -> %d" % (off, len(got), len(nb)))
        b[off:off + len(got)] = nb + bytes(len(got) - len(nb))
        done.append((off, new))
    return bytes(b), done


def _pack(a):
    i, plain, room = a
    blob = banlz.compress_record(plain)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(plain)
    return i, blob


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    heads = sorted(h for h, _ in items)

    edited = {}
    for ri, table in sorted(FIX.items()):
        hdr, dec = items[ri]
        plain, done = edit(bytes(dec), table)
        edited[ri] = (hdr, plain)
        for off, new in done:
            print("  rec%-4d %#08x  %s" % (ri, off, new))
    print("restored the name macro in %d strings across %d records"
          % (sum(len(t) for t in FIX.values()), len(edited)))
    if not write:
        f.close()
        print("(dry run - pass --write to apply)")
        return 0

    jobs = max(1, (os.cpu_count() or 4) - 2)
    pool = multiprocessing.Pool(jobs)
    ji = []
    for i, (h, d) in edited.items():
        ji.append((i, d, min([q for q in heads if q > h] or [SIZE]) - h))
    packed = dict(pool.map(_pack, ji))
    pool.close()
    pool.join()

    for i, (hdr, _plain) in edited.items():
        blob = packed[i]
        nxt = min([h for h in heads if h > hdr] or [SIZE])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % i
        raw[hdr:hdr + len(blob)] = blob
        for k in range(hdr + len(blob), nxt):
            raw[k] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw))
             if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(h for h, _ in edited.values()), \
        "unexpected records changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("wrote %d records, and only those" % len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
