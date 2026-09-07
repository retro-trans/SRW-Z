# -*- coding: utf-8 -*-
u"""Split one STAGE record's rows into chunks for a fresh translation pass.

Each chunk is a JSON list of rows carrying everything a translator needs and
nothing else: the japanese, our current english, the speaker plate, the byte
slot the field must fit, and the box it is drawn in. Rows are kept in script
order and never renumbered - the key (rec:sha1(jp):occurrence) is the only
identity, and the apply step pairs by it.

Also emits a terms file per chunk: every glossary entry whose japanese appears
in that chunk, so a translator does not have to guess a name.

Usage: make_stage_chunks.py <rec> <n-chunks> <out-dir>
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    rec = sys.argv[1]
    n = int(sys.argv[2])
    out = sys.argv[3]
    if not os.path.isdir(out):
        os.makedirs(out)
    d = json.load(open(os.path.join(ROOT, 'analysis', 'proofread',
                                    'dialogue.json'), encoding='utf-8'))
    g = json.load(open(os.path.join(ROOT, 'analysis', 'glossary.json'),
                       encoding='utf-8'))
    rows = d[rec]
    size = (len(rows) + n - 1) // n
    print('rec%s: %d rows -> %d chunks of <=%d' % (rec, len(rows), n, size))
    for i in range(n):
        part = rows[i * size:(i + 1) * size]
        if not part:
            continue
        blob = ' '.join(r['jp'] or '' for r in part)
        terms = {k: v for k, v in g.items() if k and k in blob}
        slim = []
        for r in part:
            speaker = r['en'].split('\n')[0] if '\n' in r['en'] else ''
            body_budget = r['slot'] - len(speaker.encode('cp932')) - 1
            slim.append({
                'key': r['key'],
                'speaker': speaker,
                'jp': r['jp'],
                'current_en': r['en'],
                'slot_bytes': r['slot'],
                'body_budget_bytes': body_budget,
                'box': r['box'],
                'max_lines': 3,
                'px_limit': r['pxlimit'],
            })
        p = os.path.join(out, 'stage_rec%s_chunk%d.json' % (rec, i + 1))
        json.dump({'rec': int(rec), 'chunk': i + 1, 'rows': slim,
                   'terms': terms},
                  open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('  %s  %d rows, %d glossary terms' % (p, len(slim), len(terms)))


main()
