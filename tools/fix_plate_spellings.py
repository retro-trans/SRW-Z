# -*- coding: utf-8 -*-
u"""Speaker plates that render under two different english spellings.

The plate is drawn beside every line a character speaks, so a japanese
plate with two english forms contradicts itself on screen. Auditing every
plate found 25 such names.

This applies only the ones where the GLOSSARY and the disc majority
agree. Each substitution is scoped to rows whose JAPANESE actually
contains the name, which matters for リンク -> "Linck": an unscoped sweep
of "Link" would rewrite the ordinary english word.

    フィル      Phil 102 / Fil 2          カトック   Katock 53 / Katokk 43
    テクス      Tex 40 / Tecs 22          ミーシャ   Micha 39 / Mischa 17
    ジョゼフ    Joseph 50 / Jozef 2       リンク     Linck 26 / Link 11
    チュイル    Chuil 14 / Chuille 6      ギッザー   Gizzer 14 / Gizzar 5
    ブラヤ      Braya 8 / Blaya 3 / Baraya 3
    マードック  Murdock 7 / Murdoch 3     マンマン   Manman 5 / Mannan 2
    セシル      Cecil 3 / Cecile 4        シトラン   Shitoran 5 / Citron 2 / Citran 2
    連邦軍艦長  Fed Captain 26 / Fed． Captain 12

DELIBERATELY NOT SWEPT - these are two different characters sharing one
plate, and unifying them would be the error:

    レイ    Rey 385 / Ray 77   Rey Za Burrel (SEED) vs Ray Beams
                               (Eureka Seven). See [[two-rei-characters]].
    シュバルツ Schwarzwald 58 / Schwarz 37  the glossary holds BOTH,
                               シュバルツ -> Schwarz and シュバルツバルト ->
                               Schwarzwald, so the plate is shared by
                               Gundam X's Schwarz Bruder and Big O's
                               Schwarzwald. Needs classifying per scene.

ALSO NOT SWEPT, awaiting a ruling: ローラ (glossary says Lola, disc says
Lora 28 to 1), ガッハ (glossary says Gaha, disc says Gahha 13 to 5), and
バレター / ロロット / ヴォダラク僧, which are absent from the glossary
entirely.

Usage: fix_plate_spellings.py <iso> <jp-iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import fix_shadow_angels as S      # rewrap()

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = '\n'

# japanese name -> (settled english, [wrong spellings])
NAMES = {
    u'フィル': (u'Phil', [u'Fil']),
    u'カトック': (u'Katock', [u'Katokk']),
    u'テクス': (u'Tex', [u'Tecs']),
    u'ミーシャ': (u'Micha', [u'Mischa']),
    u'ジョゼフ': (u'Joseph', [u'Jozef']),
    u'リンク': (u'Linck', [u'Link']),
    u'チュイル': (u'Chuil', [u'Chuille']),
    u'ギッザー': (u'Gizzer', [u'Gizzar']),
    u'ブラヤ': (u'Braya', [u'Blaya', u'Baraya']),
    u'マードック': (u'Murdock', [u'Murdoch']),
    u'マンマン': (u'Manman', [u'Mannan']),
    u'セシル': (u'Cecil', [u'Cecile']),
    u'シトラン': (u'Shitoran', [u'Citron', u'Citran']),
    u'連邦軍艦長': (u'Fed Captain', [u'Fed． Captain', u'Fed. Captain']),
    # akurasu 2026-09-09: Loran's alias is Laura (episode titles "Laura's
    # Cow", "Laura's Distant Howl"). The glossary said Lola and the disc
    # said Lora 28 to 1 - both wrong, the same shape as Touma. This is the
    # long-open ローラ item; see [[naming-baseline-wiki]].
    u'ローラ': (u'Laura', [u'Lora', u'Lola']),
    # akurasu spells the Xabungle medic Medick, matching the disc majority
    # and contradicting the glossary's 'Medic'.
    u'メディック': (u'Medick', [u'Medic']),
    # Neither akurasu nor the wider web documents these four, so the user
    # left the choice to me (2026-09-09). Decided on the katakana:
    #   ガッハ is ga-h-ha, so Gahha. "Gappa" would be ガッパ - the disc's own
    #   "I'm Gappa Wingail" self-introduction is a misreading, and the plate
    #   majority happens to be right.
    u'ガッハ': (u'Gahha', [u'Gappa', u'Gaha']),
    u'バレター': (u'Valetar', [u'Valter']),
    #   僧 is specifically a monk, which outweighs a 9-to-7 split on a role
    #   label rather than a name.
    u'ヴォダラク僧': (u'Vodarac Monk', [u'Vodarac Priest']),
    #   dead tie 3/3, so match this project's wapuro style (シトラン->Shitoran)
    u'ロロット': (u'Rorotto', [u'Lolot']),
    u'暗殺部隊': (u'Assassin', [u'Assassin Unit', u'Assassins']),
    # 鉄甲鬼: plate and glossary both say Tekkouki (146 v 54), but the
    # glossary contradicted itself with メカ鉄甲鬼 -> 'Mecha Tekkoki'.
    # One pattern fixes both, since "Mecha Tekkoki" contains it.
    u'鉄甲鬼': (u'Tekkouki', [u'Tekkoki']),
    # "Alliance Ofcr" is a byte squeeze, not a choice - every comparable
    # plate spells the rank out. 7 of 9 rows have room; the other 2 are
    # one byte short and are relocated.
    u'連合軍士官': (u'Alliance Officer', [u'Alliance Ofcr']),
    # RESOLVED 2026-09-09, and the opposite of what I first assumed.
    # シュバルツ is NOT a shared plate: ブルーダー appears in ZERO records, so
    # Gundam X's Schwarz Bruder is never named on this disc, while the Big O
    # markers シュバルツバルト / ゼーバッハ appear in rec24/45/108/113/131.
    # Every unmarked row is Roger on Big Duo, Alan Gabriel and 'the truth' -
    # Schwarzwald. The glossary's シュバルツ -> Schwarz was the source.
    u'シュバルツ': (u'Schwarzwald', [u'Schwarz']),
}


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

    counts, touched, over = {}, {}, 0
    for rec, (h, d) in enumerate(live):
        jb = bytes(jp[rec])
        for ve, (vj, p) in EP.pair(bytes(d), jb).items():
            j, _ = EP.text_at(jb, vj)
            e, room = EP.text_at(bytes(d), ve)
            if not j or not e:
                continue
            new = e
            for jname, (good, wrongs) in NAMES.items():
                if jname not in j:
                    continue
                for w in wrongs:
                    # flatten so a wrapped name is not missed, then re-wrap
                    rx = re.compile(r'(?<![A-Za-z])' + re.escape(w).replace(
                        r'\ ', r'\s+') + r'(?![A-Za-z])')
                    flat = ' '.join(new.split())
                    if not rx.search(flat):
                        continue
                    sp, sep, body = new.partition(NL)
                    if sep:
                        width = max(len(x) for x in body.split(NL))
                        nb2 = rx.sub(good, ' '.join(body.split()))
                        cand = rx.sub(good, sp) + NL + S.rewrap(nb2, width)
                    else:
                        cand = rx.sub(good, new)
                    if cand != new:
                        counts[good] = counts.get(good, 0) + 1
                        new = cand
            if new == e:
                continue
            nb = new.encode('cp932')
            if len(nb) > room - 1:
                over += 1
                continue
            z = bytes(d).find(b"\x00", ve)
            d[ve:ve + len(nb)] = nb
            for x in range(ve + len(nb), max(z, ve + len(nb))):
                d[x] = 0
            d[ve + len(nb)] = 0
            touched[rec] = True
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("  %-16s %d" % (k, v))
    print("rows over budget, skipped: %d" % over)
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
