# -*- coding: utf-8 -*-
"""Translate the 463 dialogue fields the extractor never saw (see gen_missing3).

Compositional: 64 SPEAKERS x 136 BODIES + 27 HEADERS, rather than 230 whole
strings. Names come from analysis/glossary.json where present; the 23 speakers
missing from it were resolved by counting existing usage across rec*_en.py so
spellings match what already ships (Touga 55 vs Toga 15, Kei 62 vs Katsura 11,
Tekkoki 182 vs Tekkouki 7, Gyukenki 65, Goushi to match Zushi/Shishi/Ryoshi/Onshi).

Slots are TIGHT - '勝平\\n「香月…」' is 15 bytes in a 16-byte slot, and English
needs a NUL terminator, so a full 'Kappei\\n"Kazuki..."' (18B) does not fit. The
FIT ladder trims punctuation before words, and anything still over budget is
REPORTED and left Japanese rather than mangled.

Output: analysis/missing3_en.json  {japanese_field: english}
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPEAKERS = {
    u"勝平": "Kappei", u"竜馬": "Ryouma", u"麗花": "Reika", u"サンドマン": "Sandman",
    u"不動": "Fudo", u"頭翅": "Zushi", u"一太郎": "Ichitaro", u"大介": "Daisuke",
    u"甲児": "Kouji", u"闘志也": "Toshiya", u"詩翅": "Shishi", u"恵子": "Keiko",
    u"琉菜": "Runa", u"兵左衛門": "Heizaemon", u"宇宙太": "Uchuta", u"鉄也": "Tetsuya",
    u"源五郎": "Gengoro", u"ライラ": "Lila", u"カミーユ": "Kamille", u"花江": "Hanae",
    u"音翅": "Onshi", u"千代錦": "Chiyonishiki", u"弓": "Yumi", u"両翅": "Ryoshi",
    u"万丈": "Banjo", u"ロベルト": "Roberto", u"ジェリド": "Jerid", u"ヘンケン": "Henken",
    u"カクリコン": "Kacricon", u"弁慶": "Benkei", u"ジャマイカン": "Jamaican",
    u"クワトロ": "Quattro", u"雷太": "Raita", u"ひかる": "Hikaru", u"エマ": "Emma",
    u"フォウ": "Four", u"アムロ": "Amuro", u"ブライト": "Bright", u"梅江": "Umee",
    u"オルソン": "Olson", u"香月": "Kazuki",
    # not in glossary - resolved from existing usage counts
    u"$n": "$n", u"斗牙": "Touga", u"？？？": "???", u"桂": "Kei",
    u"総裁": "Chairman", u"風見": "Kazami", u"理恵": "Rie", u"鉄甲鬼": "Tekkoki",
    u"剛翅": "Goushi", u"太一郎": "Taichiro", u"市民": "Citizen",
    u"連邦軍兵": "EA Soldier", u"暗殺部隊": "Assassin", u"浜本": "Hamamoto",
    u"ヒューギ": "Hugi", u"Ｄ．Ｏ．Ｍ．Ｅ．": "D.O.M.E.", u"エィナ": "Eina",
    u"ＤＣ兵": "DC Soldier", u"マウアー": "Mouar", u"少女": "Girl",
    u"少年": "Boy", u"キラケン": "Kiraken", u"第８号": "No.8",
}

BODIES = {
    # --- interjections / trailing off ---
    u"………": "...", u"…！": "...!", u"！": "!", u"！？": "!?",
    u"$n…": "$n...", u"$n！！": "$n!!",
    u"了解": "Roger", u"了解！": "Roger!", u"了解…！": "Roger...!",
    u"乾杯": "Cheers", u"同感": "Agreed", u"御意…": "As you wish...",
    u"ＧＯ！": "GO!",
    u"何…": "What...", u"何…？": "What...?", u"何？": "What?",
    # 'Reinforcements?' cannot fit 'Kappei\n"..."' in a 16-byte slot - one word,
    # nothing for the trim ladder to cut. 'Help?' carries the same beat.
    u"再戦？": "Again?", u"援軍？": "Help?", u"噂？": "Rumors?",
    u"駄目…！": "No...!",
    u"夢？": "A dream?", u"夢…？": "A dream...?", u"約束？": "A promise?",
    u"罪…？": "A sin...?", u"納得…": "I see...", u"少女…": "A girl...",
    u"君…？": "You...?", u"日輪…？": "Nichirin...?",
    u"人間爆弾？": "Human bombs?", u"脱獄囚…？": "An escapee...?",
    u"弱点！？": "A weak point!?", u"復讐…！？": "Revenge...!?",
    u"挨拶…！？": "A greeting...!?", u"地球外生命体…": "Alien life...",
    u"大特異点…": "Great Singularity...", u"●、●●…": "*, **...",
    u"学習要綱第３３章第１項…": "Study Guide Ch.33 Sec.1...",
    # --- names being called ---
    u"勝平…": "Kappei...", u"勝平！": "Kappei!", u"勝平！！": "Kappei!!",
    u"勝平君…": "Kappei...", u"…勝平君…": "...Kappei...",
    u"香月…": "Kazuki...", u"斗牙…": "Touga...", u"斗牙！": "Touga!",
    u"浜本…": "Hamamoto...", u"麗花…": "Reika...", u"理恵…": "Rie...",
    u"闘志也…": "Toshiya...", u"宇宙太…": "Uchuta...", u"宇宙太！": "Uchuta!",
    u"…甲児君…": "...Kouji...", u"親方…": "Boss...", u"双翅！": "Soshi!",
    u"博士…": "Doctor...", u"博士！": "Doctor!",
    u"大尉…": "Captain...", u"大尉…！": "Captain...!",
    u"月影長官…": "Director Tsukikage...",
    u"風見博士…": "Dr. Kazami...", u"風見博士！": "Dr. Kazami!",
    u"不動…！": "Fudo...!", u"不動司令！": "Commander Fudo!",
    u"不動司令…": "Commander Fudo...", u"不動司令…！": "Commander Fudo...!",
    u"桂木桂…！？": "Kei Katsuragi...!?",
    u"牛剣鬼…": "Gyukenki...", u"牛剣鬼！": "Gyukenki!",
    u"牛剣鬼殿！": "Lord Gyukenki!",
    u"鉄甲鬼…": "Tekkoki...", u"鉄甲鬼…！": "Tekkoki...!",
    u"グラン∑！": "Gran Sigma!",
    u"創聖合体！": "Genesis Combine!",
    u"炎皇！　合神！！": "Enou! Combine!!",
    u"ビアルⅠ世、沈降！": "Bial I, descend!",
    u"勝平！　宇宙太、恵子！": "Kappei! Uchuta, Keiko!",
    u"勝平！　宇宙太、恵子！！": "Kappei! Uchuta, Keiko!!",
    # --- 48-byte ---
    u"あの黒いＭｋ－Ⅱ、エマ中尉の…": "That black Mk-II, Lt. Emma's...",
    u"グラン∑、忌々しいマシンだ！": "Gran Sigma, that cursed machine!",
    u"ゴッド∑グラヴィオンだって！？": "God Sigma Gravion!?",
    u"ゴッド∑グラヴィオンだと！？": "God Sigma Gravion!?",
    u"Ｍｋ－Ⅱが後退する！": "The Mk-II is retreating!",
    u"黒いＭｋ－Ⅱ！\n　ティターンズなの！？":
        'The black Mk-II!\nIs it the Titans!?',
    # --- 64-byte ---
    u"あの黄色い機体、\n　Ｍｋ－Ⅱをかばったのか！":
        'That yellow unit\nshielded the Mk-II!',
    u"だが、あの時のグラン∑は\n　未完成だった…":
        'But the Gran Sigma back then\nwas unfinished...',
    u"よく来たな、勝平。\n　ここがビアルⅠ世のブリッジだ":
        'Welcome, Kappei.\nThis is Bial I\'s bridge.',
    u"ガンダムＭｋ－Ⅱ用の装備、\n　Ｇディフェンサー…":
        'Equipment for the Mk-II,\nthe G-Defenser...',
    u"ガンダムＭｋ－Ⅱ！\n　アーガマから救援が来たか！":
        'Gundam Mk-II!\nAid from the Argama!',
    u"ビアルⅠ世、Ⅱ世、Ⅲ世、\n　ドッキングします！":
        'Bial I, II and III,\ndocking now!',
    u"三位一体の攻撃だ！\n　かわせまい、Ｍｋ－Ⅱ！":
        'A three-way attack!\nYou can\'t dodge, Mk-II!',
    u"勝平、\n　Ⅱ世とⅢ世は自動操縦で動いているんだ":
        'Kappei, II and III are\nrunning on autopilot.',
    u"勝平、皆さん！\n　このビアルⅠ世に乗るんだ！":
        'Kappei, everyone!\nGet aboard Bial I!',
    u"勝平！\n　こちらビアルⅠ世の一太郎だ！":
        'Kappei! This is Ichitaro\non Bial I!',
    u"Ｍｋ－Ⅱ…！\n　こいつだけは、ここで仕留める…！":
        'Mk-II...! This one I\nfinish here...!',
    u"Ｍｋ－Ⅱ…！\n　奴だけは、ここで仕留める…！":
        'Mk-II...! That one I\nfinish here...!',
    u"Ｍｋ－Ⅱ、こいつだけは\n　ここで仕留める…！":
        'The Mk-II - this one\nI finish here...!',
    u"Ｍｋ－Ⅱのパイロット！\n　お前は危険だ！！":
        'Pilot of the Mk-II!\nYou are dangerous!!',
    # --- 80-byte ---
    u"Ⅲ世はうちが諏訪湖で見つけて、\n　ここまで運んできたのよ":
        'We found III at Lake Suwa\nand hauled it all the way here.',
    u"あのビアルⅡ世は、うちの父さんが\n　東京湾から発見したんだ":
        'My dad found that Bial II\ndown in Tokyo Bay.',
    u"あれはグラン∑（シグマ）。\n　プロトタイプのグラヴィオンだ":
        'That is Gran Sigma,\nthe prototype Gravion.',
    u"おじいさん、これ以上は\n　ビアルⅠ世の高度を維持出来ません":
        'Grandfather, we can\'t hold\nBial I\'s altitude any longer!',
    u"じゃあ、このビアルⅠ世と\n　ザンボエースについて教えて下さいよ":
        'Then tell me about this Bial I\nand the Zambo Ace.',
    u"そのＭｋ－Ⅱに乗っているのは、\n　エマ・シーン中尉か…！？":
        'The one in that Mk-II is\nLt. Emma Sheen...!?',
    u"でも、ガンダムＭｋ－Ⅱは\n　ティターンズカラーのはずでは…":
        'But the Gundam Mk-II should\nbe in Titans colors...',
    u"な、難民の人達のいたビアルⅢ世の\n　第２倉庫が爆発しました！":
        'B-Bial III\'s No.2 hold, where\nthe refugees were, exploded!',
    u"カミーユ・ビダン…！\n　$cのパイロット…\n　乗機はガンダムＭｋ－Ⅱ…":
        'Kamille Bidan...!\nPilot of $c...\nUnit: Gundam Mk-II...',
    u"ガンダムＭｋ－Ⅱ…カミーユ…！\n　ライラの仇を討たせてもらうぞ！":
        'Gundam Mk-II... Kamille...!\nI\'ll avenge Lila!',
    u"ガンダムＭｋ－Ⅱに続いて、\n　いただかせてもらうとするか":
        'After the Gundam Mk-II,\nI\'ll be taking this one too.',
    u"ガンダムＭｋ－Ⅱは連邦軍のものです！\n　返してもらいます！":
        'The Gundam Mk-II belongs to\nthe Federation! Give it back!',
    u"サンドマン様！\n　グラン∑に乗るために不死の体を\n　失ったのですか！？":
        'Lord Sandman! Did you lose\nyour immortal body to pilot\nthe Gran Sigma!?',
    u"人数が多過ぎて\n　ビアルⅡ世とⅢ世の倉庫に\n　分かれてもらってますけどね":
        'There are too many, so we split\nthem between the holds of\nBial II and III.',
    u"勝平君…あなたは\n　ビアルⅠ世に戻った方がいいんじゃない？":
        'Kappei... shouldn\'t you be\ngetting back to Bial I?',
    u"宇宙を舞う二つの∑…。\n　気高く美しく…そして、雄々しく！":
        'Two Sigmas dancing in space...\nNoble, beautiful... and brave!',
    u"艦長、Ｍｋ－Ⅱのパイロットは\n　我々に投降する気のようだ":
        'Captain, the Mk-II\'s pilot\nmeans to surrender to us.',
    # --- 96-byte ---
    u"どうするんです、おじいさん！？\n　まだ半数の人達がビアルⅡ世に\n　収容されています！":
        'What do we do, Grandfather!?\nHalf of them are still\naboard Bial II!',
    u"グラン∑が完全に完成すれば、\n　創星機として星をも創る力を\n　発揮する事が出来る…":
        'Once the Gran Sigma is complete,\nas a Genesis Machine it can\nwield the power to make stars...',
    u"グラン∑よ…。\n　お前の力を再び使う時が来た。\n　だが、過ちを繰り返しはしない！":
        'Gran Sigma... the time has come\nto use your power again. But I\nwill not repeat my mistake!',
    u"ジュリィ…！\n　トリニティエネルギーの制御を！\n　回路を∑１１３６に切り替えろ！":
        'Julie...! Control the Trinity\nEnergy! Switch the circuit\nover to Sigma 1136!',
    u"ジークめ！\n　ソルグラヴィオンのコアにグラン∑を\n　持ち出してくるとはな！":
        'Curse you, Zeke! Bringing out\nthe Gran Sigma as Sol Gravion\'s\ncore!',
    u"上々だ。\n　…こいつはブロンコⅡとエマーンの\n　デバイスのハイブリッドってわけか":
        'Excellent. ...So this is a hybrid\nof the Bronco II and an Emaan\ndevice.',
    u"創星機グラン∑が完全に完成すれば、\n　ランビアスの汚染も食い止められ…":
        'If the Genesis Machine Gran Sigma\nis completed, Lanbias\' pollution\ncould be stopped too...',
    u"大気圏内なら、モビルスーツだろうと\n　この俺とブロンコⅡの敵じゃないってのに":
        'In atmosphere, not even a Mobile\nSuit is a match for me and\nthe Bronco II.',
    u"待て、エマ中尉！\n　まだＭｋ－Ⅱは戦えるはずだ！\n　敵前逃亡は許さんぞ！":
        'Wait, Lt. Emma! The Mk-II can\nstill fight! I won\'t allow\ndesertion before the enemy!',
    u"舞え、ゴッド∑グラヴィオン！\n　戦士達と共に雄々しく！\n　そして、美しく！！":
        'Dance, God Sigma Gravion!\nBravely, with the warriors!\nAnd beautifully!!',
    u"行こう、闘志也君。\n　私もこのゴッド∑グラヴィオンで\n　君達と共に戦う！":
        'Let\'s go, Toshiya. I too will\nfight beside you in this\nGod Sigma Gravion!',
    u"銃を向けた義兄に対して、\n　私は自衛のためにグラン∑を\n　呼び寄せた…":
        'Against my brother-in-law\'s gun,\nI called the Gran Sigma\nto defend myself...',
    # --- 112-byte ---
    u"ああ、そうだよ。\n　俺のオーガスは前の世界のブロンコⅡと\n　エマーンのドリファンドを融合させたんだ":
        'Yeah, that\'s right. My Orguss\nfused the old world\'s Bronco II\nwith an Emaan Drifand.',
    u"あなただって見たはずだ！\n　ティターンズがＭｋ－Ⅱを取り返すために\n　俺のお袋を利用したのを！":
        'You must have seen it too!\nThe Titans used my own mother\nto take back the Mk-II!',
    u"え～、ビアルⅠ世へ。\n　こちら、勝平…東京を襲っているのは\n　ガイゾックじゃないみたいだぜ":
        'Uh, to Bial I. This is Kappei...\nWhatever is hitting Tokyo,\nit doesn\'t look like Gaizok.',
    u"お前にはグリプスでＭｋ－Ⅱを\n　奪われた時からの借りがある！\n　その前の空港の件も含めてな！":
        'I\'ve owed you since you took\nthe Mk-II at Gryps! That business\nat the airport too!',
    u"その美しき思い出に決着をつけるため\n　私はあなたを討とう！\n　このゴッド∑グラヴィオンで！":
        'To settle those beautiful\nmemories, I will strike you down!\nWith this God Sigma Gravion!',
    u"その美しき思い出に決着をつけるため、\n　私はあなたを討とう！\n　このゴッド∑グラヴィオンで！":
        'To settle those beautiful\nmemories, I will strike you down!\nWith this God Sigma Gravion!',
    u"エゥーゴで開発したＭｋ－Ⅱ用の\n　増加装備だ。装甲と火力が大幅に\n　アップする事になる":
        'Add-on gear for the Mk-II,\ndeveloped by AEUG. It greatly\nraises armor and firepower.',
    u"クワトロ大尉とガンダムＭｋ－Ⅱを\n　囮に使ったんだ。ティターンズの連中は\n　飛びついてくるさ":
        'We used Lt. Quattro and the\nGundam Mk-II as bait. The Titans\nwill jump right at it.',
    u"新連邦…時空制御装置…実験…。\n　２日後…１８：００…Ｘ１３Ｙ２４…\n　危険…危険…危険…":
        'New Federation... spacetime\ncontrol device... test...\n2 days... 18:00... X13Y24...',
    u"Ｚガンダムはカミーユに使ってもらう。\n　エマ中尉…Ｍｋ－Ⅱは基本的に君が\n　運用するといい":
        'Kamille will take the Z Gundam.\nLt. Emma... you should handle\nthe Mk-II from here on.',
}

# scene headers: keep the game's fullwidth centering + ～ marks, English inside
HEADERS = {
    u"駿河湾": "Suruga Bay",
    u"駿河湾　漁港": "Suruga Bay Fishing Port",
    u"駿河湾　沿岸": "Suruga Bay Coast",
    u"漁港付近": "Near the Fishing Port",
    u"連合軍入間基地　尋問室": "EA Iruma Base Interrogation",
    u"ビアルⅠ世　ブリッジ": "Bial I Bridge",
    u"新地球連邦軍　高官用執務室": "New Federation Officers' Room",
    u"月光号　格納庫": "Getter Hangar",
    u"月光号　医務室": "Getter Infirmary",
    u"新地球連邦政府　賢人会議": "New Federation Council",
    u"新地球連邦本部　賢人会議": "New Federation HQ Council",
    u"新地球連邦本部　大統領執務室": "New Federation President's Office",
    u"Ｓ－１星皇帝　執務室": "S-1 Emperor's Office",
    u"最高評議会議長　執務室": "Supreme Council Chairman's Office",
    u"議長執務室": "Chairman's Office",
    u"シベリア": "Siberia",
    u"新早乙女研究所　応接室": "New Saotome Lab Reception",
    u"早乙女研究所　格納庫": "Saotome Lab Hangar",
    u"光子力研究所　司令室": "Photon Lab Command Room",
    u"光子力研究所": "Photon Power Lab",
    u"地球連邦軍本部内": "Earth Federation HQ",
    u"研究施設内": "Research Facility",
    u"営倉": "The Brig",
    u"風見私室": "Kazami's Room",
    u"風見研究室": "Kazami's Lab",
    u"バー": "The Bar",
    u"Ｄ．Ｏ．Ｍ．Ｅ．内部": "Inside D.O.M.E.",
}

# Two lines cannot hold the Speaker\n"body" convention at all: a 16-byte slot
# leaves 15 usable, and 'Hamamoto\n"Kappei..."' needs 20. Dropping the quotes
# alone still needs 18 - the trailing ellipsis has to go too, which lands both
# at exactly 15. They lose the quote marks and the trailing-off beat, but the
# alternative is leaving them Japanese.
OVERRIDES = {
    u"浜本\n「勝平…」": "Hamamoto\nKappei",
    u"勝平\n「浜本…」": "Kappei\nHamamoto",
}

IDSP = u"　"
COLS = 32


def fit(en, budget):
    """Trim to fit, punctuation before words. Returns None if impossible."""
    cur = en
    while len(cur.encode("cp932", "replace")) >= budget:
        if cur.endswith("..."):
            cur = cur[:-3] + ".."
        elif cur.endswith(".."):
            cur = cur[:-2] + "."
        elif cur.endswith((".", "!", "?", '"')) and len(cur) > 1:
            cur = cur[:-1]
        elif " " in cur:
            cur = cur.rsplit(" ", 1)[0]
        else:
            return None
    return cur


def build_header(jp, budget):
    """'　　\\n　　　　　　～ビアルⅠ世　ブリッジ～' -> same shape, English inside."""
    first, rest = jp.split("\n", 1)
    core = rest.strip().strip(u"～").strip(u"〜")
    en = HEADERS.get(core)
    if en is None:
        return None
    text_cols = 4 + len(en)                 # two fullwidth ～ = 2 cols each
    pad = max(1, (COLS - text_cols) // 4)   # fullwidth space = 2 cols
    out = first + "\n" + IDSP * pad + u"～" + en + u"～"
    if len(out.encode("cp932", "replace")) >= budget:
        for p in range(pad - 1, 0, -1):
            out = first + "\n" + IDSP * p + u"～" + en + u"～"
            if len(out.encode("cp932", "replace")) < budget:
                return out
        return None
    return out


def main():
    src = json.load(io.open(os.path.join(WORK, "analysis", "missing3_jp.json"),
                            encoding="utf-8"))
    out = {}
    fail = []
    n_fit = 0
    for rec, rows in src.items():
        for off, budget, jp in rows:
            if jp in out:
                continue
            en = OVERRIDES.get(jp)
            if en and len(en.encode("cp932")) >= budget:
                en = None                       # override still does not fit
            if en:
                pass
            elif "\n" in jp and u"「" in jp and jp.rstrip().endswith(u"」"):
                sp, rest = jp.split("\n", 1)
                body = rest.strip()
                s_en = SPEAKERS.get(sp.strip())
                b_en = BODIES.get(body[1:-1]) if body.startswith(u"「") else None
                if s_en and b_en is not None:
                    en = fit('%s\n"%s"' % (s_en, b_en), budget)
            elif u"～" in jp or u"〜" in jp:
                en = build_header(jp, budget)
            if en:
                out[jp] = en
                n_fit += 1
            else:
                fail.append((int(rec), off, budget, jp))

    p = os.path.join(WORK, "analysis", "missing3_en.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("translated : %d unique strings" % len(out))
    print("could NOT fit / no entry: %d" % len(fail))
    for rec, off, bud, jp in fail[:40]:
        print("   rec%03d @0x%05X bud %-4d %s"
              % (rec, off, bud, json.dumps(jp, ensure_ascii=False)[:70]))
    print("\nwritten -> %s" % p)


if __name__ == "__main__":
    main()
