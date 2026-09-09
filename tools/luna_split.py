# -*- coding: utf-8 -*-
u"""Separate the two women and one machine the script calls "Luna".

Three different things render "Luna" in english:

  琉菜          Gravion. Speaker plate "Luna", 326 rows. Keeps the name.
  ルナマリア     SEED Destiny. Plate "Lunamaria", 304 rows - but Shinn calls
                her plain ルナ, and that shipped as "Luna" too.
  ベクタールナ   Aquarion's Vector Luna, a machine, routinely shortened to ルナ.

THE OBVIOUS RULE IS WRONG. It is tempting to say kanji 琉菜 is Gravion and
katakana ルナ is Lunamaria, so the split can be made mechanically. It cannot:
the script writes Gravion's Luna in katakana too - 「リィルとルナで両方から
キスしてあげるのは？」 is Lil and Luna, both Gravion - and of 26 rows whose
japanese holds a bare ルナ against an english "Luna", fifteen are the Aquarion
machine ("Vector Mars to Luna!", "who rides Luna"). Expanding on orthography
alone would have renamed a mecha after a SEED pilot.

What actually holds is the SPEAKER. Only Shinn uses the nickname for
Lunamaria, and every one of his eleven rows is unambiguous. That is the rule
here; it is narrow on purpose. Anyone extending it should re-read the rows
first, not trust the character class.

The user chose to expand the nickname (2026-09-09): her plate already reads
Lunamaria, so there is no plate churn and the reader sees the name the game
prints above the line.

"Luna" -> "Lunamaria" costs 5 bytes; rows that no longer fit are reported and
should be applied with tools/apply_lines_relocating.py.

Usage: luna_split.py [<rec> ...]      records to SKIP (mid-translation)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import reflow_dialogue as R
import apply_stage_json as A

OUT = os.path.join(ROOT, 'analysis', 'luna_split.json')
NL = '\n'

FULL = u'ルナマリア'
NICK = re.compile(u'ルナ(?!マ)')
LUNA = re.compile(r'(?<![A-Za-z])Luna(?![A-Za-z])')
# the only speaker who calls Lunamaria ルナ; see the docstring for why this is
# a speaker rule and not an orthography rule
SPEAKERS = {'Shinn'}


def main():
    skip = set(sys.argv[1:])
    adv = R.load_adv(os.path.join(ROOT, 'iso', 'srwz_cap.bin'))
    d = json.load(open(os.path.join(ROOT, 'analysis', 'proofread',
                                    'dialogue.json'), encoding='utf-8'))
    out, tight, other = {}, [], 0
    for rec, rows in d.items():
        if rec in skip:
            continue
        for r in rows:
            jp = r['jp'] or ''
            if not NICK.search(jp.partition(NL)[2].replace(FULL, '')):
                continue
            sp, _, b = r['en'].partition(NL)
            flat = ' '.join(b.split())
            if not LUNA.search(flat):
                continue
            if sp.strip() not in SPEAKERS:
                other += 1              # Gravion's Luna, or the Aquarion mech
                continue
            field = sp + NL + LUNA.sub('Lunamaria', flat)
            nf, nl = A.wrap_field(field, r['box'] == 'over-map', adv)
            if len(nf.encode('cp932')) > r['slot'] or nl > 3:
                tight.append((r['key'], len(nf.encode('cp932')), r['slot'], nl))
            out[r['key']] = field
    print('rows to expand    : %d' % len(out))
    print('  fit in place    : %d' % (len(out) - len(tight)))
    print('  need relocation : %d' % len(tight))
    print('left alone        : %d  (Gravion\'s Luna, or Vector Luna)' % other)
    for t in tight:
        print('   %s  %d>%d  %d line(s)' % t)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
