# -*- coding: utf-8 -*-
u"""Scene location captions that were never translated.

The scene caption ("Minerva Hangar", "Lutetium Base - Hall") is its own
class of string: no speaker, no 「」. Because the proofread export defines
a dialogue row by the JAPANESE 「 - see [[dialogue-identified-by-japanese-bracket]]
- these rows were never in any sheet, and no proofread pass ever saw
them. 1,281 of them ARE translated, so the class is displayed and
normally handled; 114 rows in 52 distinct captions were simply missed and
still render as kanji.

Names are taken from the disc wherever the disc already has them, never
invented. The ～...～ variant of the same caption is usually translated
even when the bare one is not, which supplies most of the vocabulary:

    ～竜神丸　デッキ～        -> ～Ryujinmaru - Deck～
    ～サルタ基地　格納庫～     -> ～Salta Base - Hangar～
    ～アガトの結晶内～        -> ～Inside the Agato Crystal～
    ～地球再生機構ディーバ　司令室～ -> ～DEAVA Command Room～

Three have no precedent anywhere on either disc and are best-effort,
marked below: 炎のＭＳ乗り, ムーン＆サン, ビューナスＡ (Venus A is the
standard Great Mazinger name).

Budgets are tight - many slots are 14-15 bytes against a 12-20 byte
japanese - so several captions are shortened rather than literal
("Inside the Agato Crystal" does not fit 15 bytes; "Agato Crystal" does).
Nothing is truncated: anything over budget is reported and skipped.

No caption may contain a digit, '.', '/' or ':' - 0x2E-0x3D are control
codes to this renderer ([[halfwidth-digits]]). Existing captions use the
full-width '．' where they need a period.

Usage: fix_scene_captions.py <iso> <jp-iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X

SEC, LBA, SIZE = 2048, 1651029, 3910128

# japanese caption -> english. Budgets are checked at run time.
CAPTIONS = {
    # --- ships and their compartments; "<Ship> <Room>" per Minerva Hangar
    u"アーガマ　食堂": u"Argama Mess",
    u"アーガマ食堂": u"Argama Mess",
    u"アーガマ　個室": u"Argama Room",
    u"ミネルバ　個室": u"Minerva Room",
    u"ミネルバ　食堂": u"Minerva Mess",
    u"ミネルバ　艦内": u"Inside Minerva",
    u"ミネルバ艦内": u"Inside Minerva",
    u"アークエンジェル　食堂": u"Archangel Mess",
    u"アイアン・ギアー　艦内": u"Inside Iron Gear",
    u"エターナル　ブリッジ": u"Eternal Bridge",
    u"エターナルブリッジ": u"Eternal Bridge",
    u"フリーデン　居間": u"Freeden Lounge",
    u"竜神丸　デッキ": u"Ryujinmaru Deck",
    u"キング・ビアル　勝平の部屋": u"King Beal - Kappei's Room",
    u"キングビアル": u"King Beal",
    # --- places
    u"シベリア平原": u"Siberian Plain",
    u"ヤーパンの天井": u"Yapan Ceiling",
    u"ボストニア城": u"Bostonia Castle",
    u"サンジェルマン城内　格納庫": u"Saint-Germain Hangar",
    u"サンジェルマン城　南の塔": u"Saint-Germain South Tower",
    u"軌道エレベーター内": u"Inside the Orbital Elevator",
    u"アガトの結晶内": u"Agato Crystal",
    u"スカブの洞窟": u"Scub Cave",
    u"サルタ基地内": u"Salta Base",
    u"サルタ基地　応接室": u"Salta Reception",
    u"オーブ　秘密ドック": u"Orb Secret Dock",
    u"オーブ　国防本部": u"Orb Defense HQ",
    u"別荘　バラ園": u"Rose Garden",
    u"ゲームセンター": u"Arcade",
    u"メサイア内部": u"Inside Messiah",
    # --- command rooms and offices
    u"デューイ司令室": u"Dewey's Office",
    u"レクイエム司令室": u"Requiem Command Room",
    u"ディーバ司令室": u"DEAVA Command",
    u"チラム総裁　執務室": u"Chiram President's Office",
    u"ゲンガナム　宮殿": u"Ghingnham Palace",
    # --- units and groups
    u"Ｇファルコン": u"G-Falcon",
    u"ビームス夫妻": u"The Beamses",
    u"アーサー親衛隊": u"Arthur's Guard",
    u"ダイアナンＡ": u"Diana A",
    # no precedent on either disc - best effort
    u"ビューナスＡ": u"Venus A",
    u"ムーン＆サン": u"Moon & Sun",
    u"炎のＭＳ乗り": u"Fiery MS Pilot",
    # --- these exact strings are already translated elsewhere on the disc;
    # copied verbatim from there rather than re-decided. Digits stay
    # FULL-WIDTH ("Zambot ３"): 0x30-0x39 are control codes here.
    u"アイアン・ギアー": u"Iron Gear",
    u"ザンボット３": u"Zambot ３",
    u"ビーター・サービス": u"Beater Service",
    u"サンドラット": u"Sandrat",
    u"黒いサザンクロス": u"Black Southern Cross",
    u"ファクトリー": u"Factory",
    u"バルディオス": u"Baldios",
    u"グランナイツ": u"Grah-Nights",
    u"ニルヴァーシュ": u"Nirvash",
    u"グローリー・スター": u"Glory Star",
}

# captions that ARE translated, but wrongly
CORRECTIONS = {
    # "King Vial" - he is King Beal everywhere else on the disc
    u"キングビアル　格納庫": u"King Beal Hangar",
    # "A．GAMA - Internal" - the ship is Argama
    u"アーガマ　艦内": u"Inside Argama",
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

    want = dict(CAPTIONS)
    want.update(CORRECTIONS)
    touched, done, skipped = {}, 0, []
    seen = set()
    for rec, (h, d) in enumerate(live):
        eb = bytes(d)
        jb = bytes(jp[rec])
        smask = X.safe_mask(jb)
        pm = F.pointer_map(eb)
        for ve, (vj, p) in EP.pair(eb, jb).items():
            j, _ = EP.text_at(jb, vj)
            if j not in want:
                continue
            e, room = EP.text_at(eb, ve)
            if e is None:
                continue
            new = want[j]
            if e == new:
                continue
            # only touch it if it is still japanese, or is a known bad one
            if e != j and j not in CORRECTIONS:
                continue
            nb = new.encode("cp932")
            if any(0x2E <= c <= 0x3D for c in nb):
                skipped.append((rec, j, new, "control byte 0x2E-0x3D"))
                continue
            if len(nb) > room - 1:
                skipped.append((rec, j, new, "%d B > budget %d"
                                % (len(nb), room - 1)))
                continue
            z = eb.find(b"\x00", ve)
            if any(ve < v < max(z, ve + len(nb)) for v in pm):
                skipped.append((rec, j, new, "pointer inside the field"))
                continue
            if not all(d[x] == 0 and smask[x]
                       for x in range(z, ve + len(nb))):
                skipped.append((rec, j, new, "growth crosses structure"))
                continue
            d[ve:ve + len(nb)] = nb
            for x in range(ve + len(nb), max(z, ve + len(nb))):
                d[x] = 0
            d[ve + len(nb)] = 0
            touched[rec] = True
            done += 1
            if j not in seen:
                seen.add(j)
                print("  %-26r -> %r" % (j, new))
    print("")
    print("caption rows written : %d (%d distinct)" % (done, len(seen)))
    print("skipped              : %d" % len(skipped))
    for rec, j, new, why in skipped[:15]:
        print("   rec%-4d %-20r -> %-24r %s" % (rec, j, new, why))
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
