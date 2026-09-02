# -*- coding: utf-8 -*-
"""Names screamed in dialogue, rendered as gibberish or as the wrong name.

Reported from a screenshot of Kamille shouting 「Fooouu!!」. The japanese is
フォウーッ！！ - he is screaming FOUR's name, drawn out - and the english had
lost the "r" entirely, leaving a meaningless noise. The same japanese line
shipped four different ways across the script.

The game's own convention for a drawn-out name is base + two extra vowels:
ステラーッ！ is "Stellaaa!", エウレカーッ！！ is "Eurekaaa!!". So フォウーッ is
"Fooour", and plain フォウ is just "Four".

Found by scanning every japanese line of the shape 「<katakana>ーッ！」 - 291 of
them - and reading the english beside it. STAGE is spliced in place, never
repacked, so a field sits at the same offset in the virgin disc and in ours,
which is what makes that comparison possible at all.

Most were already right (Stella!, Kira!, Neo!). These were not:

  Raven/「Raven!」        <- レイヴン「サンドマン！」  he is calling SANDMAN
  Holland/「...Apollonius...」 <- ホランド「デューイ！！」  wrong line entirely
  Shagia/「Orba!!」       <- オルバ is Olba in all 269 other places
  Stella/「Shin!」        <- シン is Shinn in 1334 of 1337

カシマル was checked and left alone: "Kashmir" is what the glossary and 109
other lines use, so it only looked wrong.

Usage: fix_name_shouts.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
JP_ISO = "iso/srwz.bin"

# (japanese line, corrected english). Matched per record at the offset where
# the japanese sits, so the right instance is always the one rewritten.
FIXES = [
    (u"カミーユ\n「フォウーッ！！」", u"Kamille\n「Fooour!!」"),
    (u"カミーユ\n「フォウーッ！」",   u"Kamille\n「Fooour!」"),
    (u"カミーユ\n「フォウ！！」",     u"Kamille\n「Four!!」"),
    (u"カミーユ\n「フォウ！」",       u"Kamille\n「Four!」"),
    (u"レイヴン\n「サンドマン！」",   u"Raven\n「Sandman!」"),
    (u"ホランド\n「デューイ！！」",   u"Holland\n「Dewey!!」"),
    (u"シャギア\n「オルバーッ！！」", u"Shagia\n「Olbaaa!!」"),
    (u"ステラ\n「シン！」",          u"Stella\n「Shinn!」"),
    (u"アスラン\n「シン！」",        u"Athrun\n「Shinn!」"),
]


# Plain substring corrections, applied anywhere in a STAGE field. The field
# keeps its extent (NUL-padded) so no intra-record offset moves.
# ステラ is Stella in the glossary and everywhere else in the script; five
# lines still said Stellar.
SUBS = [("Stellar", "Stella")]


def apply_subs(d):
    """Rewrite fields containing a SUBS key, holding each field's extent."""
    n = 0
    for old, new in SUBS:
        ob, nb = old.encode("cp932"), new.encode("cp932")
        p = 0
        while True:
            p = bytes(d).find(ob, p)
            if p < 0:
                break
            a = p
            while a > 0 and d[a - 1] != 0:
                a -= 1
            z = bytes(d).find(b"\x00", p)
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            field = bytes(d[a:z])
            fixed = field.replace(ob, nb)
            if len(fixed) <= k - a - 1:
                d[a:k] = fixed + b"\x00" * (k - a - len(fixed))
                n += 1
            p = a + len(fixed)
    return n


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    jraw = load(JP_ISO)
    jitems = banlz.decompress_all(jraw)
    jrec = [bytes(d) for h, d in jitems if isinstance(h, int) and d is not None]

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, d in items if isinstance(h, int) and d is not None)
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]

    total = 0
    for ri, (hdr, data) in enumerate(live):
        if ri >= len(jrec):
            break
        j, d = jrec[ri], bytearray(data)
        touched = 0
        for jp, en in FIXES:
            jb, eb = jp.encode("cp932"), en.encode("cp932")
            p = 0
            while True:
                p = j.find(jb, p)
                if p < 0:
                    break
                # the same offset in our record holds the english field
                z = bytes(d).find(b"\x00", p)
                if z < 0:
                    break
                k = z
                while k < len(d) and d[k] == 0:
                    k += 1
                cur = bytes(d[p:z])
                if cur != eb and len(eb) <= k - p - 1:
                    print("   rec%-3d %#08x %-24r -> %r"
                          % (ri, p, cur.decode("cp932", "replace").replace("\n", "/"),
                             en.replace("\n", "/")))
                    d[p:k] = eb + b"\x00" * (k - p - len(eb))
                    touched += 1
                p += len(jb)
        got = apply_subs(d)
        if got:
            print("   rec%-3d %d field(s) with a substring fix" % (ri, got))
        touched += got
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

    print("\n%d line(s) corrected" % total)
    if write and total:
        after = [h for h, d in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and d is not None]
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
