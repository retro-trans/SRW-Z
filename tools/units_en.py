# -*- coding: utf-8 -*-
"""Canon English names for the 117 unit slots still Japanese in COMPDATA.

Hand-authored rather than transliterated: Hepburn gives 'MajingaZ', 'Zanbotto3'
and 'BiaruI' where the established names are Mazinger Z, Zambot 3 and Bial I.
Budgets are the real NUL slots (slot - 1, terminator must survive); the few
7-byte slots force contractions and are flagged REVIEW.

Bial I/II/III matches the spelling used by the _M3 dialogue pass. Note the
existing script has drift here (King Bial / King Beal / King Vial appear in
different records) - worth one normalisation pass later.
"""

UNITS = {
    # --- Mazinger / Getter / Grendizer ---
    u"マジンガーＺ": "Mazinger Z",
    u"ダイアナンＡ": "Diana A",
    u"ビューナスＡ": "Venus A",
    u"合体百鬼ロボ": "Hyakki Robo",          # 15B slot: 'Combined Hyakki Robo' is 20
    # --- Zambot 3 ---
    u"ザンボット３": "Zambot 3",
    u"ザンブル": "Zambull",
    u"ザンベース": "Zambase",
    u"ビアルⅠ世": "Bial I",
    u"ビアルⅡ世": "Bial II",
    u"ビアルⅢ世": "Bial III",
    u"海鳴王": "Kaimeio",                   # REVIEW: 7-byte slot
    u"陸震王": "Rikuoh",                    # REVIEW: 'Rikushin' is 8B, slot is 7
    # --- Daitarn 3 ---
    u"ダイターン３": "Daitarn 3",
    # --- Baldios ---
    u"ニューパルサバーン": "New Pulsa Burn",
    u"バルディプライズ": "Baldi Prize",
    u"キャタレンジャー": "Cata Ranger",
    u"フィクサー１": "Fixer-1",
    # --- Orguss ---
    u"オーガスⅡ": "Orguss II",
    u"オーガスⅡ・フライヤー": "Orguss II Flyer",
    u"オーガスⅡ・オルソン": "Orguss II Olson",
    u"モラーバー・マーイ": "Mollabar Mai",
    u"モラーバー・リーア": "Mollabar Lia",
    u"ブロンコⅡ": "Bronco II",
    u"イシュキック・コマンダーⅡ": "Ishkick Commander II",
    u"ナイキック　アテナ機": "Nikick Athena",
    u"ナイキック　オルソン機": "Nikick Olson",
    # --- Xabungle ---
    u"ウォーカーギャリア": "Walker Galliar",
    u"アイアン・ギアー（ＬＳ）": "Iron Gear (LS)",
    u"アイアン・ギアー（ＷＭ）": "Iron Gear (WM)",
    u"トラッド１１": "Trad 11",
    u"ギア・ギア（ＬＳ）": "Gear Gear (LS)",
    u"ギア・ギア（ＷＭ）": "Gear Gear (WM)",
    # --- Zeta Gundam ---
    u"ガンダムＭｋ－Ⅱ": "Gundam Mk-II",
    u"Ｚガンダム": "Z Gundam",
    u"メタス（ＭＡ）": "Methuss (MA)",
    u"ガザＣ": "Gaza C",
    u"ジ・Ｏ": "The O",
    u"フライングアーマー": "Flying Armor",
    # --- Turn A ---
    u"スモー（シルバータイプ）": "SUMO (Silver)",
    u"スモー（ゴールドタイプ）": "SUMO (Gold)",
    u"ターンＸ": "Turn X",
    # --- Gundam X ---
    u"ガンダムエックスディバイダー": "Gundam X Divider",
    u"ガンダムエックス・ディバイダー": "Gundam X Divider",
    u"ガンダムエアマスター・バースト": "Gundam Airmaster Burst",
    u"ガンダムレオパルド・デストロイ": "Gundam Leopard Destroy",
    u"ガンダムＤＸ＋Ｇファルコン": "Gundam DX + G-Falcon",
    u"Ｇファルコン": "G-Falcon",
    u"ジェニス改・エニルカスタム": "Jenice Kai Ennil Custom",
    u"ガンダムヴァサーゴＣＢ": "Gundam Virsago CB",
    u"ガンダムアシュタロンＨＣ": "Gundam Ashtaron HC",
    u"Ｄ．Ｏ．Ｍ．Ｅ．Ｇビット": "D.O.M.E. G-Bit",
    # --- SEED Destiny ---
    u"フォースインパルスガンダム": "Force Impulse Gundam",
    u"ソードインパルスガンダム": "Sword Impulse Gundam",
    u"ブラストインパルスガンダム": "Blast Impulse Gundam",
    u"ガナーザクウォーリア": "Gunner ZAKU Warrior",
    u"ブレイズザクファントム": "Blaze ZAKU Phantom",
    u"ゲイツＲ": "GuAIZ R",
    u"ジン・ハイマニューバ２型": "GINN High Maneuver 2",
    u"ダガーＬ": "Dagger L",
    u"Ｓフリーダムガンダム": "Strike Freedom Gundam",
    u"∞ジャスティスガンダム": "Infinite Justice Gundam",
    u"ストライクルージュ": "Strike Rouge",
    u"エールストライクガンダム": "Aile Strike Gundam",
    u"ゴンドワナ級": "Gondwana-class",
    u"コア・スプレンダー": "Core Splendor",
    u"チェストフライヤー": "Chest Flyer",
    u"レッグフライヤー": "Leg Flyer",
    u"ソードシルエット": "Sword Silhouette",
    u"フォースシルエット": "Force Silhouette",
    u"シャトル": "Shuttle",
    # --- Overman King Gainer ---
    u"ゲイナーＢ（ブラック）": "Gainer B (Black)",
    u"チェルノボーグ": "Chernobog",
    u"バッハクロン": "Bakhron",
    u"スヴァロギッチ": "Svarogich",
    # --- Big O ---
    u"ビッグデュオ・インフェルノ": "Big Duo Inferno",
    u"ベック・ビクトリー・デラックス": "Beck Victory Deluxe",
    u"ベック・ザ・グレートＲＸ３": "Beck the Great RX3",
    u"プレイリードッグ": "Prairie Dog",
    # --- Gravion ---
    u"ゴッド∑グラヴィオン": "God Sigma Gravion",
    u"ソル∑グラヴィオン": "Sol Sigma Gravion",
    u"ソルジャーゼラバイア": "Soldier Zeravire",
    u"Ｇアタッカー": "G-Attacker",
    u"Ｇストライカー": "G-Striker",
    u"Ｇドリラー": "G-Driller",
    u"Ｇシャドウ": "G-Shadow",
    u"Ｇｅｏミラージュ": "Geo Mirage",
    u"Ｇｅｏジャベリン": "Geo Javelin",
    u"Ｇｅｏキャリバー": "Geo Caliber",
    u"Ｇｅｏスティンガー": "Geo Stinger",
    u"グラン∑": "Gran Sigma",
    u"グランフォートレス": "Gran Fortress",
    # --- Aquarion ---
    u"アクエリオンエンジェル": "Aquarion Angel",
    u"ケルビムマーズ": "Cherubim Mars",
    u"ケルビム・ヴェルルゼバ": "Cherubim Verrulzeba",
    u"ケルビム・シュルルクベラ": "Cherubim Shurrukbera",
    u"ケルビム・イスキューロン": "Cherubim Iskyuron",
    u"グラーヴェ・ケルビム": "Grave Cherubim",
    u"ミラーソーラーアクエリオン": "Mirror Solar Aquarion",
    u"ミラーアクエリオンマーズ": "Mirror Aquarion Mars",
    u"ミラーアクエリオンルナ": "Mirror Aquarion Luna",
    u"収穫獣": "Harvest",                    # REVIEW: 7-byte slot ('Harvest Beast' is 13)
    u"ベクターデルタ": "Vector Delta",
    u"ベクターアルファ": "Vector Alpha",
    u"ベクターオメガ": "Vector Omega",
    # --- Eureka Seven ---
    u"ニルヴァーシュ　ｓｐｅｃ２": "Nirvash spec2",
    u"ニルヴァーシュ　ｓｐｅｃ３": "Nirvash spec3",
    u"ニルヴァーシュ　ｔｈｅ　ＥＮＤ": "Nirvash theEND",
    u"ターミナス　６０６": "Terminus 606",
    u"ターミナス　８０８": "Terminus 808",
    u"ターミナス　９０９": "Terminus 909",
    u"ターミナス　３０３": "Terminus 303",
    u"モンスーノ１０": "Monsoono 10",
    u"モンスーノ２０": "Monsoono 20",
    u"塔州連邦軍空中戦艦": "Federation Airship",
    u"白鳥号": "Swan",
    u"スカイフィッシュ": "Skyfish",
    u"光球": "Sphere",                       # REVIEW: 7-byte slot ('Light Orb' is 9)
}
