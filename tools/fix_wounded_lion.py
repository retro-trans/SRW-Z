# -*- coding: utf-8 -*-
"""Normalise the Sphere name \u50b7\u3060\u3089\u3051\u306e\u7345\u5b50, and fix one misread Ziene line.

THE SPHERE. \u50b7\u3060\u3089\u3051\u306e\u7345\u5b50 is a proper noun - the Sphere inside Gunleon - and the
script rendered it SIX different ways across 11 lines:

    Scarred Lion 4, wounded lion 3, scarred lion 1, Wounded Lion 1,
    battered lion 2

The Super Robot Wars wiki, which is this project's naming baseline, calls it
the **Sphere of the Wounded Lion**, so "Scarred Lion" is the wrong one and the
capitalised "Wounded Lion" is right. All 11 are normalised here.

Every replacement is the same length or shorter, so wrapping is unchanged
except where an article had to move; those rows are re-wrapped by hand below
and every one stays within 3 body lines and 33 columns.

THE ZIENE LINE. rec57 0x00a320 misplaced a modifier:

    JP  \u3042\u306e\u65e5\u3001\u6b6a\u3081\u3089\u308c\u305f\u904b\u547d\u304b\u3089\u5f7c\u306f\u79c1\u3092\u6551\u3063\u3066\u304f\u308c\u308b\u2026
    EN  "That day, from the warped fate... he'll save me..."

\u3042\u306e\u65e5 modifies \u6b6a\u3081\u3089\u308c\u305f\u904b\u547d - the fate that was warped THAT DAY, the day the
bomb went off. The english reads as though the rescue happens that day, which
is the opposite of the point: the warping is in the past, the rescue is the
thing she is still waiting for.

Usage: fix_wounded_lion.py <iso> [--write]
"""
import multiprocessing
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = chr(10)
KO, KC = u"\u300c", u"\u300d"

# (rec, offset, expected english, replacement)
FIX = [
 (57,  0x008ff0,
  u"Asakim" + NL + KO + u"A wounded lion is a pitiful" + NL +
  u"sight. But your opponent will" + NL + u"be..." + KC,
  # wrapped to 30, not 34: a 3-line row wider than 30 that would still fit
  # at 30 with ascii quotes is the v1.55 crash signature verify_boxes
  # exists to catch, and "The Wounded Lion is a pitiful" is 31 with the
  # corner brackets. Caught by the gate, not by eye.
  u"Asakim" + NL + KO + u"The Wounded Lion is a" + NL +
  u"pitiful sight. But your" + NL + u"opponent will be..." + KC),
 (83,  0x00f280,
  u"Asakim" + NL + KO + u"No... that battered lion has" + NL +
  u"already woken..." + KC,
  u"Asakim" + NL + KO + u"No... the Wounded Lion has" + NL +
  u"already woken..." + KC),
 (84,  0x014d82,
  u"Asakim" + NL + KO + u"Reacting to the Sphere, the" + NL +
  u"Scarred Lion awakens! You two are" + NL + u"the finest sacrifices!!" + KC,
  u"Asakim" + NL + KO + u"Reacting to the Sphere, the" + NL +
  u"Wounded Lion awakens! You two are" + NL + u"the finest sacrifices!!" + KC),
 (84,  0x014f32,
  u"Asakim" + NL + KO + u"Even the Scarred Lion is" + NL +
  u"surprised by you. And remembering" + NL + u"days gone by, he weeps..." + KC,
  u"Asakim" + NL + KO + u"Even the Wounded Lion is" + NL +
  u"surprised by you. And remembering" + NL + u"days gone by, he weeps..." + KC),
 (84,  0x0123f0,
  u"Ziene" + NL + KO + u"That glimpse of power from the" + NL +
  u"Scarred Lion ... that's what you" + NL + u"crave, isn't it." + KC,
  u"Ziene" + NL + KO + u"That glimpse of power from the" + NL +
  u"Wounded Lion... that's what you" + NL + u"crave, isn't it." + KC),
 (101, 0x00f2f0,
  u"???" + NL + KO + u"The Scarred Lion's Sphere is" + NL +
  u"reacting to the Source's power." + KC,
  u"???" + NL + KO + u"The Wounded Lion's Sphere is" + NL +
  u"reacting to the Source's power." + KC),
 (111, 0x012740,
  u"Asakim" + NL + KO + u"All that's left is to make you" + NL +
  u"scream in pain and fully awaken" + NL + u"the scarred lion." + KC,
  u"Asakim" + NL + KO + u"All that's left is to make you" + NL +
  u"scream in pain and fully awaken" + NL + u"the Wounded Lion." + KC),
 (140, 0x0190d0,
  u"Asakim" + NL + KO + u"The wounded lion laments his" + NL +
  u"fate, and sheds tears of blood." + KC,
  u"Asakim" + NL + KO + u"The Wounded Lion laments his" + NL +
  u"fate, and sheds tears of blood." + KC),
 (140, 0x019360,
  u"Asakim" + NL + KO + u"The one who owned it before the" + NL +
  u"wounded lion didn't fully awaken." + NL + u"So the Sphere fled at death." + KC,
  u"Asakim" + NL + KO + u"The one who owned it before the" + NL +
  u"Wounded Lion didn't fully awaken." + NL + u"So the Sphere fled at death." + KC),
 (142, 0x018850,
  u"Asakim" + NL + KO + u"Match over, battered lion..." + KC,
  u"Asakim" + NL + KO + u"Match over, Wounded Lion..." + KC),
 # the misread modifier
 (57,  0x00a320,
  u"Ziene" + NL + KO + u"That day, from the warped" + NL +
  u"fate... he'll save me... from the" + NL +
  u"memory of that endless pain..." + KC,
  u"Ziene" + NL + KO + u"He'll save me from the fate" + NL +
  u"warped that day... from the" + NL +
  u"memory of that endless pain..." + KC),
]


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


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

    plains = {}
    for ri, off, want, new in FIX:
        b = bytearray(plains.get(ri, bytes(items[ri][1])))
        z = b.find(b"\x00", off)
        got = bytes(b[off:z])
        if got == new.encode("cp932"):
            print("rec%-4d %#08x  already applied" % (ri, off))
            continue
        if got != want.encode("cp932"):
            raise SystemExit("rec%d %#08x holds %r\n           expected %r"
                             % (ri, off, got.decode("cp932", "replace"), want))
        k = z
        while k < len(b) and b[k] == 0:
            k += 1
        nb = new.encode("cp932")
        if len(nb) >= k - off:
            raise SystemExit("rec%d %#08x needs %d bytes, room %d"
                             % (ri, off, len(nb) + 1, k - off))
        body = new.split(NL)[1:]
        if len(body) > 3 or max(cols(l) for l in body) > 34:
            raise SystemExit("rec%d %#08x: %d lines, widest %d cols"
                             % (ri, off, len(body), max(cols(l) for l in body)))
        # the replacement may be longer OR shorter than what it replaces,
        # so rewrite the whole verified run - string plus its NUL padding -
        # rather than assuming it shrinks. Nothing past k is touched.
        b[off:k] = nb + bytes(k - off - len(nb))
        plains[ri] = bytes(b)
        print("rec%-4d %#08x  %2d cols  %s"
              % (ri, off, max(cols(l) for l in body),
                 new.replace(NL, u" | ")))
    print("\n%d lines in %d records" % (len(FIX), len(plains)))
    if not write:
        print("(dry run - pass --write to apply)")
        return 0

    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    ji = [(i, plains[i],
           min([q for q in heads if q > items[i][0]] or [SIZE]) - items[i][0])
          for i in plains]
    packed = dict(pool.map(_pack, ji))
    pool.close()
    pool.join()
    for i in plains:
        hdr = items[i][0]
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
    assert changed == sorted(items[i][0] for i in plains), \
        "unexpected records changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("wrote %d records, and only those" % len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
