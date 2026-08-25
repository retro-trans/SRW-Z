# -*- coding: utf-8 -*-
"""Record which rows in a DeepSeek record need later Claude review, into
analysis/deepseek_review.json:
  - jp_untranslated: rows still over-budget (will be left Japanese on apply -> MUST fix)
  - machine_trimmed: rows the mech trimmer altered (lower-confidence -> optional polish)

Usage: deepseek_mark.py <N> [<N> ...]
Detects untranslated rows as any row whose current EN exceeds its budget (those
get skipped by apply_stage and stay JP).
"""
import importlib.util as u
import json
import os
import sys

WORK = r'E:\Projects\SRW Z\_work'
REV = WORK + r'\analysis\deepseek_review.json'


def bl(s):
    return len(s.encode('cp932', 'replace'))


def main():
    rev = json.load(open(REV)) if os.path.exists(REV) else {}
    for a in sys.argv[1:]:
        n = int(a)
        p = 'rec%03d_en.py' % n
        s = u.spec_from_file_location('m%d' % n, p)
        m = u.module_from_spec(s)
        s.loader.exec_module(m)
        wk = {r['i']: r for r in json.load(
            open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))}
        over = sorted(i for i in m.T if i in wk and bl(m.T[i]) > wk[i]['budget'])
        rev['rec%03d' % n] = {
            'jp_untranslated': over,   # will stay Japanese after apply
            'row_count': len(m.T),
            'over_count': len(over),
            'note': 'DeepSeek-translated. jp_untranslated rows exceed byte budget '
                    'and remain Japanese in-game until a targeted Claude pass fixes them.',
        }
        print('rec%03d: %d untranslated (stay JP), %d/%d english'
              % (n, len(over), len(m.T) - len(over), len(m.T)))
    json.dump(rev, open(REV, 'w'), indent=1)
    total = sum(v['over_count'] for v in rev.values())
    print('review manifest updated: %d records, %d rows flagged for later fix'
          % (len(rev), total))


if __name__ == "__main__":
    main()
