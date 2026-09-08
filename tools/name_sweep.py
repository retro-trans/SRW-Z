# -*- coding: utf-8 -*-
u"""Apply every name spelling this project has settled, game-wide.

This is the standing record of the decisions, not a one-off script: re-run it
after any translation pass, because a fresh chunk will reintroduce a spelling
its translator saw elsewhere on the disc.

Each entry is justified by evidence on the disc, never by the glossary alone -
[[naming-baseline-wiki]] holds for new names, but the glossary has shipped
wrong entries and cannot overrule what the game already draws on screen.

THE PLATE WINS. Where a name is spelled one way on the speaker plate and
another in body text, the body is wrong: the plate is drawn beside every line
that character speaks, so a body that disagrees contradicts the screen itself.
That rule settled Bloodman, Touga, Bask, Teral, Jeela, Rietz and Mu, and needed
no ruling from anyone ([[plate-beats-body-for-names]]).

Where no plate exists the disc majority wins, and where the english is simply
wrong about the japanese - 神 read as "God" when it is the surname Jin - it is
a mistranslation, not a preference.

大尉 SPLITS BY CHARACTER, by the user's ruling of 2026-09-08: Lowen is
Captain, Quattro is Lt. The rank word is the same japanese, but each man's
majority form is the one the playtester has already seen, so neither is swept
to match the other. Astonaige, Darrow and Mouar were settled the same day.

STILL OPEN, deliberately absent from this file: ローラ, Loran's alias, which
ships as Lora, Lola and Laura. See [[rank-taii-inconsistent]].

Usage: name_sweep.py [<rec> ...]      records to SKIP (mid-translation)
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

OUT = os.path.join(ROOT, 'analysis', 'name_sweep.json')
NL = '\n'

# ordered - a compound is repaired before the name inside it is unified
SUBS = [
    # the earlier Shin -> Shinn sweep hit 神勝平, whose surname reads Jin, and
    # produced Shinn Asuka's name on Kappei's line. rec6 and rec26 already had
    # the right form, and rec26's japanese even glosses it 神（じん）勝平.
    (r'Kappei\s+Shinn?(?![A-Za-z])', 'Jin Kappei'),
    (r'(?<![A-Za-z])God Family(?![A-Za-z])', 'Jin Family'),
    # 連合 is Alliance; the faction was split Alliance/Union/Federation
    (r'(?<![A-Za-z])Skullmoon(?![A-Za-z])', 'Skull Moon'),
    (r'(?<![A-Za-z])Skull Moon Union(?![A-Za-z])', 'Skull Moon Alliance'),
    (r'(?<![A-Za-z])Skull Moon Federation(?![A-Za-z])', 'Skull Moon Alliance'),
    # plate says Jeela 38, Teral 361, Rietz 46, Mu 39, Bloodman 151,
    # Touga 498, Bask 69 - and never the stray
    (r'(?<![A-Za-z])Zira(?![A-Za-z])', 'Jeela'),
    (r'(?<![A-Za-z])Jira(?![A-Za-z])', 'Jeela'),
    (r'(?<![A-Za-z])Zeera(?![A-Za-z])', 'Jeela'),
    (r'(?<![A-Za-z])Terral(?![A-Za-z])', 'Teral'),
    (r'(?<![A-Za-z])Leets(?![A-Za-z])', 'Rietz'),
    (r'(?<![A-Za-z])Mwu(?![A-Za-z])', 'Mu'),
    (r'(?<![A-Za-z])Bradman(?![A-Za-z])', 'Bloodman'),
    (r'(?<![A-Za-z])Toga(?![A-Za-z])', 'Touga'),
    (r'(?<![A-Za-z])Basque(?![A-Za-z])', 'Bask'),
    (r'(?<![A-Za-z])Maintener(?![A-Za-z])', 'Maintainer'),
    # no plate to appeal to: disc majority
    (r'(?<![A-Za-z])Cosmozaurus(?![A-Za-z])', 'Cosmosaurus'),
    (r'(?<![A-Za-z])Cosmo Zaurus(?![A-Za-z])', 'Cosmosaurus'),
    (r'(?<![A-Za-z])Quinstain(?![A-Za-z])', 'Quinstein'),
    (r'(?<![A-Za-z])Spaceoid(?![A-Za-z])', 'Spacenoid'),
    # ranks and names the user settled on 2026-09-08. 大尉 is deliberately
    # NOT unified across characters: each keeps the form already on screen.
    (r'(?<![A-Za-z])Lieutenant Lowen(?![A-Za-z])', 'Captain Lowen'),
    (r'(?<![A-Za-z])Lt\. Lowen(?![A-Za-z])', 'Captain Lowen'),
    (r'(?<![A-Za-z])Captain Quattro(?![A-Za-z])', 'Lt. Quattro'),
    (r'(?<![A-Za-z])Lieutenant Quattro(?![A-Za-z])', 'Lt. Quattro'),
    (r'(?<![A-Za-z])Capt\. Quattro(?![A-Za-z])', 'Lt. Quattro'),
    (r'(?<![A-Za-z])Astonage(?![A-Za-z])', 'Astonaige'),
    (r'(?<![A-Za-z])Dawell(?![A-Za-z])', 'Darrow'),
    (r'(?<![A-Za-z])Darwell(?![A-Za-z])', 'Darrow'),
    (r'(?<![A-Za-z])Mauar(?![A-Za-z])', 'Mouar'),
    (r'(?<![A-Za-z])Mauer(?![A-Za-z])', 'Mouar'),
    (r'(?<![A-Za-z])Kouji(?![A-Za-z])', 'Koji'),
    (r'(?<![A-Za-z])Vice General(?![A-Za-z])', 'Brigadier General'),
]


def main():
    skip = set(sys.argv[1:])
    adv = R.load_adv(os.path.join(ROOT, 'iso', 'srwz_cap.bin'))
    d = json.load(open(os.path.join(ROOT, 'analysis', 'proofread',
                                    'dialogue.json'), encoding='utf-8'))
    out, tight, hits = {}, [], {}
    for rec, rows in d.items():
        if rec in skip:
            continue
        for r in rows:
            sp, _, b = r['en'].partition(NL)
            # BOTH LINES. Sweeping only the body left 22 speaker plates still
            # reading "Mauar" after the user had settled on Mouar - and the
            # plate is the copy the player actually reads, drawn beside every
            # line that character speaks.
            flat = ' '.join(b.split())
            nsp, nb = sp, flat
            for pat, rep in SUBS:
                fixed = re.sub(pat, rep, nsp)
                if fixed != nsp:
                    hits[rep] = hits.get(rep, 0) + 1
                    nsp = fixed
                fixed = re.sub(pat, rep, nb)
                if fixed != nb:
                    hits[rep] = hits.get(rep, 0) + 1
                    nb = fixed
            if nsp == sp and nb == flat:
                continue
            field = nsp + NL + nb
            nf, nl = A.wrap_field(field, r['box'] == 'over-map', adv)
            if len(nf.encode('cp932')) > r['slot'] or nl > 3:
                tight.append((r['key'], len(nf.encode('cp932')), r['slot'], nl))
            out[r['key']] = field
    for k in sorted(hits):
        print('  -> %-22s %d hit(s)' % (k, hits[k]))
    print('rows to fix: %d   over slot (relocate or reword): %d'
          % (len(out), len(tight)))
    for t in tight:
        print('   %s  %d>%d  %d line(s)' % t)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
