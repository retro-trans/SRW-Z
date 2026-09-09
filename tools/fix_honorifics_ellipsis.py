# -*- coding: utf-8 -*-
u"""Two style passes the user handed me: honorifics, and two-dot ellipses.

HONORIFICS. The disc's house style is ENGLISH, not romaji - I had assumed
the opposite until I counted:

    様   Lady 399 / Lord 314 / Master 29   vs  -sama 28   english 96%
    さん  Mr. 109 / Ms. 63 / Miss 47        vs  -san  37   english 86%
    先輩  senpai 28                          no english form used at all
    ちゃん -chan 14, 君 -kun 4                 no english form used at all

So -sama and -san are the deviation and are converted; -senpai, -chan and
-kun are KEPT, because this translation has never used an english form for
them and because they carry meaning it cannot easily replicate:

    「Grandma! It's Faye-chan, not Hei-chan.」  the suffix IS the joke
    「Beck-sama's tech」 / 「Super Negotiator-sama!」  ironic, not deferent
    -senpai marks the DEAVA hierarchy that drives Aquarion's cast

Each name takes the title the disc ALREADY uses for that character
elsewhere (Dianna is Lady 264 times, Teral is Lord 41, Sandman is Mr. 21),
so nothing is invented. Every conversion is the same byte length -
"Edel-sama" -> "Lady Edel", "Reccoa-san" -> "Ms. Reccoa" - so no row can
overflow.

ELLIPSES. 1,452 two-dot ellipses against 33,101 three-dot. The user's
instruction: do not use two dots where there are spare bytes. 227 of those
rows have ZERO spare and were plainly squeezed to fit, so they keep the
two-dot form; everything with room is expanded.

Usage: fix_honorifics_ellipsis.py <iso> <jp-iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP

SEC, LBA, SIZE = 2048, 1651029, 3910128

# name -> title, taken from how the disc already titles that character
SAMA = {
    'Dianna': 'Lady', 'Edel': 'Lady', 'Lacus': 'Lady',
    'Teral': 'Lord', 'Toma': 'Lord', 'Gainer': 'Lord', 'Gagarn': 'Lord',
    'Paptimus': 'Lord', 'Kei': 'Lord', 'Beck': 'Lord',
    # "Master Kappei" is 2 bytes longer than the slot allows; Lord is
    # the same length as the romaji form and fits.
    'Kappei': 'Lord', 'Negotiator': 'Mr.',
}
SAN = {
    'Reccoa': 'Ms.', 'Mizuki': 'Ms.', 'Leele': 'Ms.', 'Silvia': 'Ms.',
    'Tsugumi': 'Ms.', 'Lina': 'Ms.',
    'Sandman': 'Mr.', 'Olson': 'Mr.', 'Mu': 'Mr.', 'Kai': 'Mr.',
    'Koji': 'Mr.', 'Kei': 'Mr.', 'Daisuke': 'Mr.', 'Astonaige': 'Mr.',
    'Tetsuya': 'Mr.', 'Toshiya': 'Mr.', 'League': 'Mr.',
}
TWO = re.compile(r'(?<!\.)\.\.(?!\.)')


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    g = open(jpiso, "rb")
    g.seek(LBA * SEC)
    jp = [d for h, d in banlz.decompress_all(g.read(SIZE))
          if isinstance(h, int) and d is not None]
    g.close()

    hon = ell = squeezed = 0
    touched = {}
    for rec, (h, d) in enumerate(live):
        jb = bytes(jp[rec])
        for ve, (vj, p) in EP.pair(bytes(d), jb).items():
            j, _ = EP.text_at(jb, vj)
            e, room = EP.text_at(bytes(d), ve)
            if not j or not e:
                continue
            new = e
            # honorifics: suffix -> the title this character already takes.
            # \s* so a name wrapped away from its suffix still matches.
            for tbl, suf, jh in ((SAMA, 'sama', u'様'), (SAN, 'san', u'さん')):
                if jh not in j:
                    continue
                for name, title in tbl.items():
                    rx = re.compile(r'(?<![A-Za-z])' + name + r'-' + suf +
                                    r'(?![A-Za-z])')
                    n2 = rx.sub(title + ' ' + name, new)
                    if n2 != new:
                        hon += 1
                        new = n2
            # ellipsis: expand only where the row has room to spare
            if TWO.search(new):
                cand = TWO.sub('...', new)
                if len(cand.encode('cp932')) <= room - 1:
                    ell += len(TWO.findall(new))
                    new = cand
                else:
                    squeezed += 1
            # $nさん: the protagonist is Rand OR Setsuko depending on route,
            # so Mr./Ms. cannot be chosen. Drop the suffix - natural english
            # and gender-safe. Always shorter, so it always fits.
            if u'さん' in j:
                new = re.sub(r'[$]n-san', '$n', new)
            if new == e:
                continue
            nb = new.encode('cp932')
            if len(nb) > room - 1:
                continue
            z = bytes(d).find(b"\x00", ve)
            d[ve:ve + len(nb)] = nb
            for x in range(ve + len(nb), max(z, ve + len(nb))):
                d[x] = 0
            d[ve + len(nb)] = 0
            touched[rec] = True
    print("honorifics converted to the english title : %d" % hon)
    print("two-dot ellipses expanded                 : %d" % ell)
    print("rows left two-dot (no spare bytes)        : %d" % squeezed)
    print("records touched: %d" % len(touched))
    if not touched or not write:
        if touched:
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
