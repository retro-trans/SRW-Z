# -*- coding: utf-8 -*-
u"""Rows that overflow only once the RUNTIME NAME is substituted.

THE BUDGET FOR THE PROTAGONIST'S NAME WAS NEVER SET. reflow_dialogue.width()
measures "$n" as the two ASCII characters $ and n - 22 px - and the reflow pass
skips any field holding a $ code outright, because the runtime width is
"UNKNOWN". export_proofread's box gate uses that same width(), so not one of
these 5,263 rows has ever been measured honestly.

What the tokens actually draw (the wider of the two protagonist routes):

    $n  Setsuko          70 px    measured as 22
    $F  Setsuko\u30fbOhara   142 px    measured as 22
    $c  \uff3a\uff25\uff35\uff34\uff28         105 px    measured as 22 - the team name is
                                 drawn FULLWIDTH, which is why it is the
                                 worst offender despite being five letters
    $f  Setsuko          70 px
    $l  Travis           57 px

231 rows overflow their box once that is accounted for, and a player reported
two of them as clipped Asakim lines. Every one of the 231 fixes by RE-WRAPPING
alone: no text is changed, no row grows, none needs a fourth line and none
leaves its slot. Only the line breaks move.

THE BUDGET IS THE DEFAULT NAME, by the user's ruling of 2026-09-10: a custom
name cannot be measured, so the two shipped defaults are the yardstick and the
wider of them wins ($F: Setsuko・Ohara 142 px beats Rand・Travis 119 px). A
player who renames the protagonist to something longer can still clip a line;
that is a known and accepted limit, not an open question - do not re-open it.

Emits fixes JSON for apply_lines_relocating.py, which is keyed, so this only
reaches rows the export produced - see [[dialogue-identified-by-japanese-bracket]]
for the pools it cannot.

Usage: fix_name_token_overflow.py <out.json>
"""
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reflow_dialogue as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'iso', 'srwz_cap.bin')
SRC = os.path.join(ROOT, 'analysis', 'proofread', 'dialogue.json')
O, C = u'\u300a', u'\u300b'          # glossary link markers
EXP = R.NAME_TOKENS      # single source of truth, used by width() itself


def main():
    out_path = sys.argv[1]
    adv = R.load_adv(ISO)

    def px(l):
        return R.width(l, adv)      # width() substitutes the tokens itself now

    def wrap(flat, limit):
        out, cur = [], u''
        for t in flat.split(u' '):
            cand = t if not cur else cur + u' ' + t
            if px(cand) <= limit:
                cur = cand
            else:
                out.append(cur)
                cur = t
        if cur:
            out.append(cur)
        return out

    d = json.load(io.open(SRC, encoding='utf-8'))
    fixes, skipped, byrec = {}, collections.Counter(), collections.Counter()
    for rec, rows in d.items():
        for r in rows:
            if not any(k in r['en'] for k in EXP):
                continue
            body = r['en'].split(u'\n')[1:]
            if max([px(l) for l in body] or [0]) <= r['pxlimit']:
                continue
            speaker = r['en'].split(u'\n')[0]
            lines = wrap(u' '.join(u' '.join(body).split()), r['pxlimit'])
            new = speaker + u'\n' + u'\n'.join(lines)
            # a glossary link split across a line break is a dead link, and a
            # dead link CRASHES the scene - see [[glossary-links]]
            if any(l.count(O) != l.count(C) for l in lines):
                skipped['link split'] += 1
                continue
            if len(lines) > 3:
                skipped['fourth line'] += 1
                continue
            if max(px(l) for l in lines) > r['pxlimit']:
                skipped['still over'] += 1
                continue
            if len(new.encode('cp932')) > r['slot'] - 1:
                skipped['over slot'] += 1
                continue
            if new == r['en']:
                continue
            fixes[r['key']] = new
            byrec[int(rec)] += 1
    print('rows re-wrapped : %d' % len(fixes))
    print('skipped         : %s' % (dict(skipped) or 'none'))
    print('records touched : %d' % len(byrec))
    json.dump(fixes, io.open(out_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('wrote %s' % out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
