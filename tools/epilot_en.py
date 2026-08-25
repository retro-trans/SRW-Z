# -*- coding: utf-8 -*-
"""Enemy pilot / generic crew designations (COMPDATA ~0x24000-0x2C000).

These are the "who is flying this" labels the squad panel shows - エゥーゴ兵,
連邦軍兵, ザフト艦長 and so on. They were never part of the PILOTS pass, which
covered NAMED characters only, so every generic enemy still read Japanese.

Slots are 22-24 bytes. Faction names follow analysis/name_source.json so these
agree with the unit list and the glossary (ZAFT, Titans, Zeon, Orb, Coralian).

予備N are unused reserve slots in the table; they are translated anyway so no
Japanese can surface if the game ever displays one.
"""

EPILOT_EN = {
    # --- factions: X兵 = soldier, X艦長 = captain, X士官 = officer ---
    "連邦軍兵": "Federation Soldier",
    "連邦軍艦長": "Federation Captain",
    "連合軍兵": "Alliance Soldier",
    "連合軍士官": "Alliance Officer",
    "所属不明兵": "Unknown Soldier",
    "革命軍兵": "Revolution Soldier",
    "政府軍兵": "Government Soldier",
    "オーブ兵": "Orb Soldier",
    "ティターンズ": "Titans",
    "ィターンズ": "Titans",          # truncated variant in the table
    "ＤＣ兵": "DC Soldier",
    "ＤＣ艦長": "DC Captain",
    "ザフト兵": "ZAFT Soldier",
    "ザフト艦長": "ZAFT Captain",
    "ザフト士官": "ZAFT Officer",
    "ジオン兵": "Zeon Soldier",
    "ジオン艦長": "Zeon Captain",
    "ギンガナム兵": "Gingannam Soldier",
    "シベ鉄隊員": "Sibe Rail Member",
    "ＳＬ兵": "SL Soldier",
    "暗殺部隊": "Assassin Squad",
    "ケルビム兵": "Cherubim Soldier",

    # --- non-human enemies ---
    "神話獣": "Mythical Beast",
    "ベガ獣": "Vega Beast",
    "円盤獣": "Saucer Beast",
    "コスモザウルス": "Cosmosaurus",
    "アルデバロンメカ": "Aldebaron Mecha",
    "メカブースト": "Mechaboost",
    "ゼラバイア": "Zeravire",
    "コーラリアン": "Coralian",

    # --- machine pilots ---
    "人工知能": "AI",
    "高性能ＡＩ": "High-Perf AI",
    "自律回路": "Autonomous Circuit",
    "制御チップ": "Control Chip",

    # --- named characters appearing in this table ---
    "トラビス": "Travis",
    "ランド": "Rand",
    "オハラ": "Ohara",
    "セツコ": "Setsuko",
    "ハマー": "Hammer",
    "デンゼル": "Denzel",
    "ワトソン": "Watson",
    "トビー": "Toby",
    "ビーター": "Beater",
    "メール": "Mel",
    "桂木": "Katsuragi",
    "桂": "Kei",
    "トリノミアス三世": "Torinomias III",
    "ヤマト": "Yamato",
    "キラ": "Kira",
    "ベルナル": "Bernal",
    "エーデル": "Edel",
}

# 予備N = unused reserve entries; filled in by epilot_apply.py so none can show
# Japanese. The digit must be FULLWIDTH under menu encoding, which the encoder
# handles.
for _i in list(range(1, 7)) + list(range(11, 16)):
    EPILOT_EN["予備" + chr(0xFF10 + _i) if _i < 10 else
              "予備" + chr(0xFF10 + _i // 10) + chr(0xFF10 + _i % 10)] = \
        "Reserve %d" % _i
