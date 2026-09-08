# -*- coding: utf-8 -*-
u"""Bring stray punctuation back to the script's own house style.

ASCII "..." is the house ellipsis by a factor of sixty: 24,087 rows use it and
402 use U+2026. Those 402 are the deviation, not a second style - a full-width
… also sits wider than three half-width dots, so it reads as a gap in an
otherwise half-width line. Translators have been fixing them one row at a time
for several stages; this does the rest.

IT COSTS A BYTE. U+2026 is two bytes in cp932 and "..." is three, so a row that
was exactly full now overflows and has to be relocated. Apply the json with
tools/apply_lines_relocating.py, which moves what it must and REPORTS what it
cannot rather than truncating.

WHAT IS DELIBERATELY LEFT ALONE:

  rec203  a radio-chat record with its own conventions - "Name： text" with a
          full-width colon and ．．． throughout, and no 「」 or speaker line at
          all. Fifteen of its thirty rows are like this. It is consistent with
          itself, and it is not addressable by the keyed apply tools anyway,
          which skip fields with no newline.
  ：      full-width colon, 25 rows. ASCII ':' is 0x3A, inside the 0x2E-0x3D
          run that the MENU blit reads as control codes, where a raw ':'
          expands to the protagonist's name ([[halfwidth-digits]]). STAGE
          dialogue takes a different path and holds raw ASCII digits happily,
          but a full-width colon may well have been chosen to dodge exactly
          that hazard, so it is not worth a byte to find out.
  ―       U+2015, one row, and the right character: cp932 has no U+2014.

Usage: punct_sweep.py [<rec> ...]      records to SKIP (mid-translation)
       then apply the json with tools/apply_lines_relocating.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import reflow_dialogue as R
import apply_stage_json as A

OUT = os.path.join(ROOT, 'analysis', 'punct_sweep.json')
NL = '\n'
ELLIPSIS = u'…'
FW_STOP = u'．'
# the full-width stop is only a stray where the record overwhelmingly uses the
# ascii one; rec203 is excluded above because it uses it as its own style
FW_STOP_RECS = {'1', '8', '25'}
SKIP_ALWAYS = {'203'}

# a word left a space before its own punctuation: 「this ends here ...!」. The
# run must be followed by whitespace, a closing bracket or the end of the body,
# so a mid-sentence 「Ryubofu ...staring」 is left for a human to word.
GAP = re.compile(u'([A-Za-z0-9])[ \t]+([,.!?]+)(?=[\\s」）)]|$)')


def clean(text, rec):
    out = text.replace(ELLIPSIS, '...')
    if rec in FW_STOP_RECS:
        out = out.replace(FW_STOP, '.')
    return GAP.sub(u'\\1\\2', out)


def main():
    skip = set(sys.argv[1:]) | SKIP_ALWAYS
    adv = R.load_adv(os.path.join(ROOT, 'iso', 'srwz_cap.bin'))
    d = json.load(open(os.path.join(ROOT, 'analysis', 'proofread',
                                    'dialogue.json'), encoding='utf-8'))
    out, tight = {}, []
    grew = 0
    for rec, rows in d.items():
        if rec in skip:
            continue
        for r in rows:
            sp, _, b = r['en'].partition(NL)
            if not b:
                continue                    # not a speaker field; not ours
            flat = ' '.join(b.split())
            nsp, nb = clean(sp, rec), clean(flat, rec)
            if nsp == sp and nb == flat:
                continue
            field = nsp + NL + nb
            nf, nl = A.wrap_field(field, r['box'] == 'over-map', adv)
            cost = len(nf.encode('cp932'))
            if cost > r['slot'] or nl > 3:
                tight.append((r['key'], cost, r['slot'], nl))
            else:
                grew += 1
            out[r['key']] = field
    print('rows to fix        : %d' % len(out))
    print('  fit in place     : %d' % grew)
    print('  need relocation  : %d' % len(tight))
    for t in tight[:15]:
        print('   %s  %d>%d  %d line(s)' % t)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
