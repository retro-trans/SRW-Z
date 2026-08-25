# -*- coding: utf-8 -*-
"""English tables for DATA/COMPDATA.BN rec0 (names, titles, bios).

Terminology: akurasu.net Z Pilot Database / Mech List romanizations.
PILOTS maps each name-field string (last/first/display are separate fields)
to English. Ambiguous strings (レイ = Ray/Rey, クライン = Clyne/Klein) are
omitted here and left Japanese for a later per-record pass.
"""

PILOTS = {
    "斗牙": "Touga",
    "桂": "Katsura",   # Gravion - kanji name missed by every pass (plate id 0x022C+)
    # original generation
    "セツコ": "Setsuko", "オハラ": "Ohara",
    "デンゼル": "Denzel", "ハマー": "Hammer",
    "トビー": "Toby", "ワトソン": "Watson",
    "ランド": "Rand", "トラビス": "Travis",
    "メール": "Mel", "ビーター": "Beater",
    "エスピオ": "Espio", "アサキム": "Asakim", "ドーウィン": "Dowin",
    # Mazinger / Great / Grendizer
    "兜": "Kabuto", "甲児": "Kouji", "弓": "Yumi", "さやか": "Sayaka",
    "剣": "Tsurugi", "鉄也": "Tetsuya", "炎": "Hono", "ジュン": "Jun",
    "ボス": "Boss", "ヌケ": "Nuke", "ムチャ": "Mucha",
    "デューク": "Duke", "フリード": "Fleed", "牧場": "Makiba",
    "ひかる": "Hikaru", "マリア": "Maria", "ルビーナ": "Rubina",
    # Getter G
    "流": "Nagare", "竜馬": "Ryouma", "隼人": "Hayato",
    "車": "Kurama", "弁慶": "Benkei", "早乙女": "Saotome", "ミチル": "Michiru",
    # God Sigma
    "壇": "Dan", "闘志也": "Toshiya", "ジュリィ": "Julie", "野口": "Noguchi",
    "吉良": "Kira", "賢作": "Kensaku",
    # Orguss
    "ケイ": "Kei", "カツラギ": "Katsuragi", "シャイア": "Shaya",
    "ミムジィ": "Mimsy", "モーム": "Mome", "マーイ": "Maaie", "リーア": "Lieea",
    "アテナ": "Athena", "オルソン": "Olson",
    # Baldios
    "マリン": "Marin", "レイガン": "Reigan", "ジャック": "Jack",
    "オリバー": "Oliver", "北斗": "Hokuto", "雷太": "Raita",
    "デビッド": "David", "ウエイン": "Uein", "フリック": "Flick", "キャリン": "Kyarin",
    # Zambot 3
    "勝平": "Kappei", "宇宙太": "Uchuta", "恵子": "Keiko",
    "神北": "Kamikita", "平左衛門": "Heizaemon", "源五郎": "Gengoro", "一太郎": "Ichitaro",
    # Daitarn 3
    "破嵐": "Haran", "万丈": "Banjo",
    # Xabungle
    "ジロン": "Jiron", "アモス": "Amos", "エルチ": "Elche", "カーゴ": "Cargo",
    "ファットマン": "Fatman", "ビッグ": "Big", "ラグ": "Rag", "ウラロ": "Uralo",
    "ブルメ": "Blume", "ダイク": "Daiku", "チル": "Chiru",
    "ビリン": "Birin", "ナダ": "Nada",
    # Zeta Gundam
    "カミーユ": "Kamille", "ビダン": "Bidan",
    "クワトロ": "Quattro", "バジーナ": "Bageena",
    "アムロ": "Amuro", "ブライト": "Bright", "ノア": "Noa",
    "トーレス": "Torres", "サエグサ": "Saegusa",
    "エマ": "Emma", "シーン": "Sheen",
    "レコア": "Reccoa", "ロンド": "Londe",
    "アポリー": "Apolly", "ロベルト": "Roberto",
    "ファ": "Fa", "ユイリィ": "Yuiry",
    "カツ": "Katz", "コバヤシ": "Kobayashi",
    "フォウ": "Four", "ムラサメ": "Murasame",
    "サラ": "Sara", "ザビアロフ": "Zabirov",
    "ヘンケン": "Henken", "ベッケナー": "Bekkener",
    "ハマーン": "Haman", "カーン": "Karn",
    "ジェリド": "Jerid", "メサ": "Mesa",
    "カクリコン": "Kacricon", "カクーラー": "Cacooler",
    "ライラ": "Lila", "ミライ": "Mirai",
    # Turn A
    "ロラン": "Loran", "セアック": "Cehack",
    "ディアナ": "Dianna", "ソレル": "Soreil",
    "ミラン": "Milan", "ソシエ": "Sochie", "ハイム": "Heim",
    "ミャシェイ": "Miashei", "クネ": "Kune",
    "コレン": "Corin", "ナンダー": "Nander",
    "ヨセフ": "Joseph", "ヤット": "Yaht",
    "ギャバン": "Gavane", "グーニー": "Gooney",
    "ハリー": "Harry", "オード": "Ord",
    "ポゥ": "Poe", "ギム": "Gym", "ギンガナム": "Ghingnham",
    # Gundam X
    "ガロード": "Garrod", "ラン": "Ran",
    "ティファ": "Tiffa", "アディール": "Adill",
    "ジャミル": "Jamil", "ニート": "Neate",
    "タイレル": "Tyrrell", "トニヤ": "Toniya", "マルメ": "Malme",
    "シンゴ": "Shingo", "モリ": "Mori",
    "ウィッツ": "Witz", "スー": "Sou",
    "ロアビィ": "Roybea", "ロイ": "Loy",
    "エニル": "Ennil", "エル": "El",
    "パーラ": "Pala", "シス": "Sys",
    "ランスロー": "Lancerow", "カリス": "Carris", "ノーチラス": "Nautilus",
    # SEED Destiny
    "シン": "Shinn", "アスカ": "Asuka",
    "ルナマリア": "Lunamaria", "ホーク": "Hawke",
    "タリア": "Talia", "グラディス": "Gladys",
    "アーサー": "Arthur", "トライン": "Trine",
    "メイリン": "Meyrin",
    "アスラン": "Athrun", "ザラ": "Zala",
    "キラ": "Kira", "ヤマト": "Yamato",
    "マリュー": "Murrue", "ラミアス": "Ramius",
    "ノイマン": "Neumann", "チャンドラ": "Chandra",
    "ラクス": "Lacus",
    "アンドリュー": "Andrew", "バルトフェルド": "Waltfeld",
    "イザーク": "Yzak", "ジュール": "Joule",
    "ムウ": "Mu",
    "スティング": "Sting", "オークレー": "Oakley",
    "アウル": "Auel", "ニーダ": "Neider",
    "ステラ": "Stella", "ルーシェ": "Loussier",
    # King Gainer
    "ゲイナー": "Gainer", "サンガ": "Sanga",
    "ゲイン": "Gain", "ビジョウ": "Bijou",
    "コダマ": "Kodama",
    "ベロー": "Bello", "コロッシャ": "Korossha",
    "ヒューズ": "Hughes", "ガウリ": "Gauli",
    "アデット": "Adette", "キスラー": "Kistler",
    "ヤッサバ": "Yassaba", "ジン": "Jin",
    "ケジナン": "Kejinan", "ダット": "Datto",
    "エンゲ": "Enge", "ガム": "Gam",
    "ジャボリ": "Jaboli", "マリエラ": "Mariela",
    "アスハム": "Asuham", "ブーン": "Boone",
    "シンシア": "Cynthia", "レーン": "Lane",
    # Big O
    "ロジャー": "Roger", "スミス": "Smith",
    "ドロシー": "Dorothy", "ウェインライト": "Wayneright",
    "ジェイソン": "Jason", "ベック": "Beck",
    "Ｔボーン": "T-Bone", "ダヴ": "Dove",
    # Gravion
    "トウガ": "Touga", "天空寺": "Tenkuuji",
    "エイジ": "Eiji", "時雨": "Shigure",
    "ルナ": "Luna", "ミヅキ": "Mizuki", "立花": "Tachibana",
    "エイナ": "Eina", "リィル": "Leele",
    "サンドマン": "Sandman", "フェイ": "Faye",
    # Aquarion
    "アポロ": "Apollo", "シルヴィア": "Silvia", "シリウス": "Sirius",
    "麗花": "Reika", "ピエール": "Pierre",
    "つぐみ": "Tsugumi", "ローゼンマイヤー": "Rosenmeier",
    "玲奈": "Rena", "グレン": "Glen", "アンダーソン": "Anderson",
    # Eureka Seven
    "レントン": "Renton", "サーストン": "Thurston",
    "エウレカ": "Eureka",
    "ホランド": "Holland", "ノヴァク": "Novak",
    "マシュー": "Matthieu", "ヒルダ": "Hilda", "ストナー": "Stoner",
    "タルホ": "Talho", "ユーキ": "Yuuki",
    "ハップ": "Hap", "ケンゴー": "Ken-Goh",
    "ムーンドギー": "Moondoggie", "ユルゲンス": "Jurgens",
    "ドミニク": "Dominic", "アネモネ": "Anemone",
    "チャールズ": "Charles", "ビームス": "Beams",
    "ザ・バレル": "Za Burrel",
    # generic enemy/grunt labels
    "ティターンズ兵": "Titans Sldr", "エゥーゴ兵": "AEUG Soldier",
    "連邦兵": "Fed Soldier", "ザフト兵": "ZAFT Soldier",
}

# ambiguous names resolved by an anchor string within the same record
# (the generic pass has already Englished the anchor fields)
AMBIG = {
    "レイ": [(b"Amuro", "Ray"), (b"Beams", "Ray"), (b"Za Burrel", "Rey")],
    "クライン": [(b"Lacus", "Clyne"), (b"Sandman", "Klein")],
}

# short fallbacks where the full name exceeds its slot
SHORT = {
    "円盤獣ゴルゴル": "Gorugoru",
    "チラム攻撃空母": "Chiram Carrier",
    "エルダー戦艦": "Eldar Ship",
    "科学要塞島": "Fortress Isle",
    "エマーン艦": "Emaan Ship",
    "ケルビム兵": "Cherudim Sldr", "チラム兵": "Chiram Sldr",
    "透明円盤": "Cloaked Saucer",
    "戦闘空母": "Battle Carrier",
    "月光号": "Gekko",
    "銀河号": "Ginga",
    # 8-byte slot (name cell = 0x6D0C0 + unit_id*8, Dijeh's cell is adjacent,
    # so it can never grow). "Type100" was 7 bytes but raw digits are CONTROL
    # CODES to the menu reader - the upgrade screen showed "TypeDijeh" (drew
    # "Type", swallowed "100"+NUL, ran into the next name). Fullwidth digits
    # need 10 bytes, so the short form must be digit-free.
    "百式": "Hyaku",
    "世界の終わる時": "World's End",
    "目覚めの日": "Awakening Day",
}

# episode/route titles (walked table at ~+0x72DA0)
TITLES = {
    "ザ・ライトスタッフ": "The Right Stuff",
    "怒れる瞳": "Angry Eyes",
    "二つの世界": "Two Worlds",
    "異星人襲来": "Alien Invasion",
    # 16-byte slot, and field_replace reserves the NUL -> 15 usable.
    # "Day of Awakening" is 16 and was silently rejected, leaving the ep-5 card
    # Japanese.
    "目覚めの日": "The Awakening",
    "超重神降臨": "The Super God Descends",
    "月光、怒りに染めて": "Moonlight Dyed in Rage",
    "世界の終わる時": "World's End",      # 15-byte budget; full phrasing was 19
    "時空破壊": "Spacetime Collapse",
    "さすらいの修理屋": "The Wandering Repairman",
}

# character-select bios (NUL-slot budget checked by the patcher)
BIOS = {
    "新型機のテストパイロットを務める地球連邦軍の兵士。\n気弱で何事にも消極的であるが、生真面目な性格で\n自分の任務を懸命に果たそうとする。":
        "An EFF soldier serving as a test pilot for a\nnew unit. Timid and passive, but earnest -\nshe gives her duty everything she has.",
}
