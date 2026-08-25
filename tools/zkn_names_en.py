# -*- coding: utf-8 -*-
"""Curated encyclopedia (図鑑) name translations: series titles and glossary
terms.

The Japanese data spells the same series several ways - with and without 「」
brackets, with and without the fullwidth space after the subtitle - so the 48
distinct PRDC/SRCE strings collapse to ~24 actual shows. Every spelling is
mapped explicitly rather than normalised, because one entry is truncated in the
original data (the SEED DESTINY one missing its closing 」) and would not
survive a round trip through a normaliser.

English display width is not a concern here: these fields held fullwidth
Japanese, which costs two half-width cells per character, so "Mobile Suit
Gundam SEED DESTINY" (31 cells) still fits where 20 fullwidth glyphs (40) did.
"""

SERIES = {
    "∀ガンダム": "Turn A Gundam",
    "「∀ガンダム」": "Turn A Gundam",
    "「オーバーマン　キングゲイナー」": "Overman King Gainer",
    "ＯＶＥＲＭＡＮキングゲイナー": "Overman King Gainer",
    "「ゲッターロボＧ」": "Getter Robo G",
    "ゲッターロボＧ": "Getter Robo G",
    "「バンプレストオリジナル」": "Banpresto Original",
    "バンプレストオリジナル": "Banpresto Original",
    # Truncated in the original data (leading char lost); same series.
    "トオリジナル": "Banpresto Original",
    "オリジナル": "Original",
    "「交響詩篇　エウレカセブン」": "Eureka Seven",
    "交響詩篇　エウレカセブン": "Eureka Seven",
    "交響詩篇エウレカセブン": "Eureka Seven",
    "「宇宙戦士　バルディオス」": "Space Warrior Baldios",
    "宇宙戦士バルディオス": "Space Warrior Baldios",
    "「戦闘メカ　ザブングル」": "Combat Mecha Xabungle",
    "戦闘メカ　ザブングル": "Combat Mecha Xabungle",
    "「機動戦士　ガンダムＳＥＥＤ　ＤＥＳＴＩＮＹ": "Mobile Suit Gundam SEED DESTINY",
    "「機動戦士　ガンダムＳＥＥＤ　ＤＥＳＴＩＮＹ」": "Mobile Suit Gundam SEED DESTINY",
    "「機動戦士ガンダムＳＥＥＤ　ＤＥＳＴＩＮＹ」": "Mobile Suit Gundam SEED DESTINY",
    "機動戦士　ガンダムＳＥＥＤ　ＤＥＳＴＩＮＹ": "Mobile Suit Gundam SEED DESTINY",
    "機動戦士ガンダムＳＥＥＤ　ＤＥＳＴＩＮＹ": "Mobile Suit Gundam SEED DESTINY",
    "「機動戦士　Ｚガンダム」": "Mobile Suit Z Gundam",
    "機動戦士　Ｚガンダム": "Mobile Suit Z Gundam",
    "機動戦士ガンダム　逆襲のシャア": "Char's Counterattack",
    "「機動新世紀　ガンダムＸ」": "After War Gundam X",
    "機動新世紀　ガンダムＸ": "After War Gundam X",
    "機動新世紀ガンダムＸ": "After War Gundam X",
    "「超時空世紀　オーガス」": "Super Dimension Century Orguss",
    "超時空世紀　オーガス": "Super Dimension Century Orguss",
    "超時空世紀オーガス": "Super Dimension Century Orguss",
    "「ＵＦＯロボ　グレンダイザー」": "UFO Robo Grendizer",
    "ＵＦＯロボ　グレンダイザー": "UFO Robo Grendizer",
    "ＵＦＯロボグレンダイザー": "UFO Robo Grendizer",
    "グレートマジンガー": "Great Mazinger",
    "マジンガーＺ": "Mazinger Z",
    "創聖のアクエリオン": "Genesis of Aquarion",
    "宇宙大帝ゴッドシグマ": "Space Emperor God Sigma",
    "無敵超人　ザンボット３": "Invincible Superman Zambot 3",
    "無敵超人ザンボット３": "Invincible Superman Zambot 3",
    "無敵鋼人　ダイターン３": "Invincible Steel Man Daitarn 3",
    "無敵鋼人ダイターン３": "Invincible Steel Man Daitarn 3",
    "超重神　グラヴィオン": "Gravion",
    "超重神グラヴィオン": "Gravion",
    "超重神　グラヴィオン　ツヴァイ": "Gravion Zwei",
    "超重神グラヴィオン　ツヴァイ": "Gravion Zwei",
    "ＴＨＥ　ビッグオー": "The Big O",
    "ＴＨＥ　ビッグオー　Ｓｅｃｏｎｄ　Ｓｅａｓｏｎ": "The Big O Second Season",
    # The COMPDATA encyclopedia list (rec0 ~0x71C40) spells these WITHOUT the
    # fullwidth space the other copies use, so they need their own keys or the
    # lookup silently misses and the entry stays Japanese.
    "機動戦士Ｚガンダム": "Mobile Suit Z Gundam",
    "オーバーマン　キングゲイナー": "Overman King Gainer",
    "ＴＨＥビッグオー": "The Big O",
    "超重神グラヴィオンツヴァイ": "Gravion Zwei",
    "マジンガ－Ｚ": "Mazinger Z",          # fullwidth HYPHEN, not a vowel mark
}

# The 52 glossary headwords (DATA_MTVZKNKW.BIN, chunk WORD).
WORDS = {
    "宇宙科学研究所": "Space Science Laboratory",
    "恐竜帝国": "Dinosaur Empire",
    "アルデバロン": "Aldebaron",
    "相克界": "Rivalry Zone",
    "イノセント": "Innocent",
    "アーサー": "Arthur",
    "カシム・キング": "Kashim King",
    "ティターンズ": "Titans",
    "エゥーゴ": "AEUG",
    "カラバ": "Karaba",
    "サイド３": "Side 3",
    "コントリズム": "Contolism",
    "ジオン・ズム・ダイクン": "Zeon Zum Deikun",
    "ミリシャ": "Militia",
    "ゲンガナム": "Gengnham",
    "フォートセバーン": "Fort Severn",
    "ナチュラル": "Natural",
    "コーディネイター": "Coordinator",
    "ブルーコスモス": "Blue Cosmos",
    "ロゴス": "Logos",
    "プラント": "PLANT",
    "プラント評議会議長": "PLANT Supreme Council Chairman",
    "ＦＡＩＴＨ": "FAITH",
    "パトリック・ザラ": "Patrick Zala",
    "ザフト": "ZAFT",
    "アーモリーワン": "Armory One",
    "アプリリウス": "Aprilius",
    "地球連合": "Earth Alliance",
    "オーブ": "Orb",
    "ウズミ": "Uzumi",
    "モルゲンレーテ社": "Morgenroete Inc.",
    "オーブ防衛戦": "Battle of Orb",
    "第２次ヤキン・ドゥーエ攻防戦": "2nd Battle of Jachin Due",
    "ラウ・ル・クルーゼ": "Rau Le Creuset",
    "ユニウス条約": "Junius Treaty",
    "エクステンデッド": "Extended",
    "ブロックワード": "Block Word",
    "エビデンス・ゼロワン": "Evidence 01",
    "エクソダス": "Exodus",
    "シベリア鉄道": "Siberian Railway",
    "オーバーマンバトル": "Overman Battle",
    "オーバーコート": "Overcoat",
    "スカブコーラル": "Scub Coral",
    "トラパー": "Trapar",
    "サマー・オブ・ラブ": "Summer of Love",
    "リフ": "Lifting",
    "ウィール": "Wheel",
    "ＳＯＦ": "SOF",
    "ヴォダラク": "Vodarac",
    "ジョン・ヘンリ": "John Henry",
    "ＵＮ": "UN",
    "グローリー・スター": "Glory Star",
}
