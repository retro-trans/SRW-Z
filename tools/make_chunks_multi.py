# -*- coding: utf-8 -*-
u"""Split several STAGE records into translation chunks in one go.

Same output shape as make_stage_chunks.py, but a chunk may span records - some
stages ship as several files (stage 50 is stg_086a..d) and splitting each one
separately would leave tiny chunks.

Usage: make_chunks_multi.py <out-dir> <n-chunks> <rec> [<rec> ...]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    out = sys.argv[1]
    n = int(sys.argv[2])
    recs = sys.argv[3:]
    if not os.path.isdir(out):
        os.makedirs(out)
    d = json.load(open(os.path.join(ROOT, 'analysis', 'proofread',
                                    'dialogue.json'), encoding='utf-8'))
    g = json.load(open(os.path.join(ROOT, 'analysis', 'glossary.json'),
                       encoding='utf-8'))
    rows = []
    for rec in recs:
        rows.extend(d[rec])
    size = (len(rows) + n - 1) // n
    print('%d rows from records %s -> %d chunks of <=%d'
          % (len(rows), ','.join(recs), n, size))
    for i in range(n):
        part = rows[i * size:(i + 1) * size]
        if not part:
            continue
        blob = ' '.join(r['jp'] or '' for r in part)
        terms = {k: v for k, v in g.items() if k and k in blob}
        slim = []
        for r in part:
            sp = r['en'].split('\n')[0] if '\n' in r['en'] else ''
            slim.append({
                'key': r['key'],
                'speaker': sp,
                'jp': r['jp'],
                'current_en': r['en'],
                'slot_bytes': r['slot'],
                'body_budget_bytes': r['slot'] - len(sp.encode('cp932')) - 1,
                'box': r['box'],
                'max_lines': 3,
                'px_limit': r['pxlimit'],
            })
        p = os.path.join(out, 'chunk%d.json' % (i + 1))
        json.dump({'records': recs, 'chunk': i + 1, 'rows': slim,
                   'terms': terms},
                  open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('  %s  %d rows, %d glossary terms' % (os.path.basename(p),
                                                    len(slim), len(terms)))


main()
