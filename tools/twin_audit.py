# -*- coding: utf-8 -*-
u"""Find dialogue rows whose route twin says something completely different.

WHY: most stages ship twice, once per protagonist route (see
[[route-records-and-pronouns]]), and the two records hold the SAME japanese
fields. So the twin is a free second opinion on every line. Where one record's
english is a full translation and the other's is a short unrelated fragment,
the short one is damage - that is exactly how the battle-caption bleed was
found in rec131/136/144/147 ([[caption-bleed-into-stage]]).

No pointer or structure gate can see this: the speaker plate stays correct
because it is regenerated from the japanese, and the field is a perfectly valid
string. Only the twin, or reading the japanese, gives it away.

The ratio is the signal. A real translation runs about 1.6-2.2x the japanese
character count; a row far under 1.0 whose twin is not is almost always wrong.

Usage: twin_audit.py [--min-ratio 1.0] [--json OUT]
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'analysis', 'proofread', 'dialogue.json')
OPENERS = (u'「', u'(', u'（')       # kagi, ascii paren, full paren


def body(field):
    b = field.partition('\n')[2].strip()
    if b[:1] in OPENERS:
        b = b[1:-1]
    return u' '.join(b.split())


def jbody(field):
    b = field.partition('\n')[2].replace(u'　', '').replace('\n', '').strip()
    if b[:1] in OPENERS:
        b = b[1:-1]
    return b


def main():
    argv = sys.argv
    lim = float(argv[argv.index('--min-ratio') + 1]) if '--min-ratio' in argv else 1.0
    out = argv[argv.index('--json') + 1] if '--json' in argv else None

    data = json.load(io.open(SRC, encoding='utf-8'))
    byjp = {}
    for rec, rows in data.items():
        for r in rows:
            jp = jbody(r['jp'] or '')
            if len(jp) < 10:
                continue
            byjp.setdefault(jp, []).append((int(rec), r))

    bad = []
    for jp, group in byjp.items():
        if len(set(g[0] for g in group)) < 2:
            continue                       # not a twin, just a repeat in one record
        ens = {}
        for rec, r in group:
            ens.setdefault(body(r['en']), []).append((rec, r))
        if len(ens) < 2:
            continue                       # both routes agree, nothing to see
        best = max(ens, key=len)
        for en, members in ens.items():
            if en == best:
                continue
            ratio = len(en) / float(len(jp))
            # the twin has to be a real translation for this to mean anything
            if ratio >= lim or len(best) / float(len(jp)) < 1.3:
                continue
            for rec, r in members:
                bad.append({'key': r['key'], 'rec': rec, 'slot': r['slot'],
                            'box': r['box'], 'jp': r['jp'], 'en': r['en'],
                            'ratio': round(ratio, 2),
                            'twin_key': ens[best][0][1]['key'],
                            'twin_rec': ens[best][0][0],
                            'twin_en': ens[best][0][1]['en']})

    bad.sort(key=lambda x: (x['rec'], x['ratio']))
    per = {}
    for b in bad:
        per[b['rec']] = per.get(b['rec'], 0) + 1
    print('twin pairs disagreeing, short side under ratio %.2f: %d' % (lim, len(bad)))
    for rec in sorted(per, key=lambda r: -per[r]):
        print('   rec%-4d %3d' % (rec, per[rec]))
    for b in bad[:12]:
        print('\n%s  ratio %.2f  slot %d' % (b['key'], b['ratio'], b['slot']))
        print('   JP   %s' % jbody(b['jp'])[:60])
        print('   ours %s' % body(b['en'])[:60])
        print('   twin %s' % body(b['twin_en'])[:60])
    if out:
        json.dump(bad, io.open(out, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('\nwrote %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
