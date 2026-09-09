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
    # リーツ: plate says Rietz 63, and all four stray "Ritz" rows have リーツ
    # in their japanese, so they are the same man
    (r'(?<![A-Za-z])Ritz(?![A-Za-z])', 'Rietz'),
    # the Gravion team: Gran Knights 65, Grand Knights 24, no plate to appeal to
    (r'(?<![A-Za-z])Grand Knights(?![A-Za-z])', 'Gran Knights'),
    (r'(?<![A-Za-z])Grand Knight(?![A-Za-z])', 'Gran Knight'),
    # 黒い歴史 is the same Turn A concept as 黒歴史 - "Black History" 296 on
    # disc, "Dark History" 0. A second english term for one japanese idea is
    # worse than a slightly loose match.
    (r'(?<![A-Za-z])Dark History(?![A-Za-z])', 'Black History'),
    # 大尉 for Roberto: Captain 11 on disc against 5 strays, same per-character
    # rule the user set for Lowen and Quattro
    (r'(?<![A-Za-z])Lieutenant Roberto(?![A-Za-z])', 'Captain Roberto'),
    (r'(?<![A-Za-z])Lt\. Roberto(?![A-Za-z])', 'Captain Roberto'),
    # 少尉 is Ensign game-wide; Athena is the one stray
    (r'(?<![A-Za-z])Lt\. Athena(?![A-Za-z])', 'Ensign Athena'),
    # 時空震動: tremor 13, quake 3, vibration 2, shock 1
    (r'(?<![A-Za-z])spacetime quake(?![A-Za-z])', 'spacetime tremor'),
    (r'(?<![A-Za-z])spacetime vibration(?![A-Za-z])', 'spacetime tremor'),
    (r'(?<![A-Za-z])spacetime shock(?![A-Za-z])', 'spacetime tremor'),
    # ゾラ 26 v 16, トレゾア: Tresor is the majority spelling
    # トーブ: the user confirmed the glossary form 2026-09-09; the disc had
    # drifted to Toube on 8 rows
    (r'(?<![A-Za-z])Toube(?![A-Za-z])', 'Thoov'),
    # body strays against a correct plate: Jeela 38, Lufira 5, Maintainer 11
    (r'(?<![A-Za-z])Jeera(?![A-Za-z])', 'Jeela'),
    (r'(?<![A-Za-z])Rufira(?![A-Za-z])', 'Lufira'),
    (r'(?<![A-Za-z])Menteiner(?![A-Za-z])', 'Maintainer'),
    # ベガ大王: the plates were unified earlier; 14 bodies still say King
    (r'(?<![A-Za-z])King Vega(?![A-Za-z])', 'Emperor Vega'),
    # the term bank had νガンダム as "v Gundam" - a different mech entirely.
    # Glossary corrected 2026-09-09; disc had 6 Nu against 2 v.
    (r'(?<![A-Za-z])v Gundam(?![A-Za-z])', 'Nu Gundam'),
    (r'(?<![A-Za-z])Xinlu(?![A-Za-z])', 'Xin Lu'),
    # all verified against the japanese in the rows themselves, not by eye:
    # every Reena/Rina row has リーナ, every Kengo row has ケンゴウ, every
    # "South Pole" row has 南極
    (r'(?<![A-Za-z])Dianna-sama(?![A-Za-z])', 'Lady Dianna'),
    # 双翅 is Futaba 49 times; three rows use the on'yomi. The route twin
    # of one of them already says Futaba for byte-identical japanese.
    (r'(?<![A-Za-z])Soshi(?![A-Za-z])', 'Futaba'),
    # Harry holds BOTH ranks: 中尉 in 49 rows and 大尉 in 15. So 中尉 takes the
    # majority "Lt. Harry" (30 v 19) and 大尉 takes "Captain Harry" - the two
    # 大尉 rows that said Lt. are fixed separately, against their own japanese.
    (r'(?<![A-Za-z])Lieutenant Harry(?![A-Za-z])', 'Lt. Harry'),
    # 125 lowercase against 18 capitalised
    (r'(?<![A-Za-z])Mobile Suit(?![A-Za-z])', 'mobile suit'),
    # 341 unhyphenated against 87 hyphenated; the hyphen form is stale
    (r'(?<![A-Za-z])space-time', 'spacetime'),
    # spelled-out ranks; "New Fed" is a standalone word 64 times (the 235 a
    # reader reported was the substring inside "New Federation")
    (r'(?<![A-Za-z])Brig\. Gen\.', 'Brigadier General'),
    (r'(?<![A-Za-z])New Earth Fed(?![A-Za-z])', 'New Earth Federation'),
    (r'(?<![A-Za-z])New Fed(?![A-Za-z])', 'New Federation'),
    (r'(?<![A-Za-z])Rep\.(?= [A-Z])', 'Representative'),
    # lone strays against a settled majority
    (r'(?<![A-Za-z])Ruchil(?![A-Za-z])', 'Lucille'),
    (r'(?<![A-Za-z])Zonder Eputa(?![A-Za-z])', 'Zonder Epta'),
    (r'(?<![A-Za-z])Council of the Wise(?![A-Za-z])', 'Council of Sages'),
    # アゲハ構想 was split three ways with no majority (Plan 5, Swallowtail 6,
    # Initiative 3); the romanised name matches how this project treats other
    # proper nouns, and "Swallowtail" is a calque invented in recs 110/111.
    (r'(?<![A-Za-z])Swallowtail [Pp]lan(?![A-Za-z])', 'Ageha Plan'),
    (r'(?<![A-Za-z])Ageha Initiative(?![A-Za-z])', 'Ageha Plan'),
    (r'(?<![A-Za-z])Reena(?![A-Za-z])', 'Lina'),
    (r'(?<![A-Za-z])Rina(?![A-Za-z])', 'Lina'),
    (r'(?<![A-Za-z])Kengo(?![A-Za-z])', 'Ken-Goh'),
    (r'(?<![A-Za-z])South Pole(?![A-Za-z])', 'Antarctica'),
    (r'(?<![A-Za-z])N\.Fed(?![A-Za-z])', 'New Federation'),
    # abbreviations against an overwhelming spelled-out majority
    (r'(?<![A-Za-z])Cmdr\.', 'Commander'),
    (r'(?<![A-Za-z])Capt\.(?! Quattro)', 'Captain'),
    (r'(?<![A-Za-z])Zola(?![A-Za-z])', 'Zora'),
    (r'(?<![A-Za-z])Trezoa(?![A-Za-z])', 'Tresor'),
    (r'(?<![A-Za-z])Trezor(?![A-Za-z])', 'Tresor'),
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
    # ローラ, Loran's female alias, shipped three ways: Lora 44, Lola 12,
    # Laura 11. The user chose the commonest. Checked first that every Lola
    # and Laura row really is ローラ in the japanese - none belonged to some
    # other character - before sweeping.
    (r'(?<![A-Za-z])Lola(?![A-Za-z])', 'Lora'),
    (r'(?<![A-Za-z])Laura(?![A-Za-z])', 'Lora'),
    # バジーナ. The user caught this on the character-library panel, which is
    # a FOURTH place names live after the dialogue, COMPDATA and the ZKN
    # library - COMPDATA already said Bajeena, so the disc contradicted
    # itself. Same length, so it fits everywhere it appears; the ZKN copies
    # need tools/zkn_rename.py, which this sweep cannot reach.
    (r'(?<![A-Za-z])Bageena(?![A-Za-z])', 'Bajeena'),
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
