# -*- coding: utf-8 -*-
"""English UI strings for the boot ELF (SLPS_258.87), keyed by file offset.

Patching is strictly in-place: each replacement must fit inside the original
string's byte length, so nothing downstream shifts and no relocation is needed.
That budget is tight, so several entries use the short form the fan community
uses rather than the full official title (e.g. "Zambot 3", not the full
"Invincible Super Man Zambot 3", which does not fit in 20 bytes).

Skill names follow the terminology established by the official Super Robot
Wars OG English releases where one exists.
"""

ELF_UI = {
    # --- pilot skills ---
    0x00335E58: "Blocking",
    0x00335F68: "Counter",
    0x00336170: "SP Up",
    0x003362C0: "Morale+ (Damage)",
    0x003363D0: "E Save",
    0x00336410: "B Save",
    0x003365B0: "Ignore Size",
    0x003367B0: "Nullifies P-type effects.",
    0x003367D0: "Hit & Away",
    0x00336928: "Newtype",
    0x003369B0: "Newtype (X)",
    0x003369D0: "Artif. Newtype",
    0x003369E8: "Category F",
    0x00336AD0: "Extended",
    0x00336AE8: "Reff Technique",
    0x00336B68: "Oversense",
    0x00336BE8: "Gamer",
    0x00336C28: "Game Champ",
    0x00336C68: "Negotiator",
    0x00336E88: "Alert",
    0x00336F90: "Fully restores unit HP.",
    0x00337028: "Mercy",
    0x00337370: "Morale +10.",
    0x00337390: "Morale +30.",
    0x00337708: "Travis",
    0x00337770: "Collection: 0%.",

    # --- series titles (short forms where the budget demands it) ---
    0x0033A0F8: "Mazinger Z",
    0x0033A110: "Great Mazinger",
    0x0033A130: "UFO Robo Grendizer",
    0x0033A150: "Getter Robo G",
    0x0033A160: "Baldios",
    0x0033A180: "God Sigma",
    0x0033A1A0: "Zambot 3",
    0x0033A1C0: "Daitarn 3",
    0x0033A1E0: "Orguss",
    0x0033A200: "Xabungle",
    0x0033A220: "Z Gundam",
    0x0033A260: "Turn A",
    0x0033A270: "After War Gundam X",
    0x0033A2C0: "Overman King Gainer",
    0x0033A2E0: "THE Big O",
    0x0033A300: "Gravion",
    0x0033A320: "Gravion Zwei",
    0x0033A340: "Aquarion",
    0x0033A360: "Eureka Seven",
    0x0033A378: "Original",

    # --- unit parts / weapons ---
    0x0033A960: "G-Defenser",
    0x0033A980: "Satellite Cannon",
    0x0033A9A0: "Sword Silhouette",
    0x0033A9C0: "Blast Silhouette",
    0x0033A9D8: "Shiranui",

    # --- system messages ---
    0x0033ABD0: "Format failed.",
    0x0033ADB0: "No save file found.",
    0x0033ADD0: "The file is corrupted.",
    0x0033AF50: "Return to title?",
}


# --- menu-visibility test batch (2026-08-12): strings visible on the unit /
# --- pilot status screens, to verify menus render ASCII (they draw via the
# --- native SJIS path, not the dialogue remap). Official OG terms where they
# --- fit the slot budget.
ELF_UI.update({
    0x00335EF0: "Prevail",          # 底力 (skill)
    0x00336510: "Focus Atk",   # 集束攻撃 (skill)
    0x00336608: "Command",          # 指揮官 (skill, 8B slot -> exactly fits)
    0x00336E18: "Strike",           # 必中 (spirit)
    0x00336EC8: "Resolve",          # 不屈 (spirit; "Fortitude" over budget)
    0x003374E0: "Trust",            # 信頼 (spirit)
    # tab headers: fullwidth (the tab style magnifies glyphs, so native
    # fullwidth art looks right there; short labels per user)
    0x00345218: "Ｕｎｉｔ",         # ユニット能力
    0x00345228: "Ｐｉｌｏｔ",       # パイロット能力
    0x00345238: "Ｍｅｃｈ",         # 機体能力
    0x00345248: "Ｗｅａｐｏｎ",     # 武器性能
})

# --- status/unit screen labels (generated batch, all exact-copy
# --- occurrences in 0x330000-0x350000; menu encoding) ---
ELF_UI.update({
    0x0033FF38: 'Melee',   # 格闘
    0x00340ED0: 'Melee',   # 格闘
    0x003410D0: 'Melee',   # 格闘
    0x00343390: 'Melee',   # 格闘
    0x00345290: 'Melee',   # 格闘
    0x00347098: 'Melee',   # 格闘
    0x003473B0: 'Melee',   # 格闘
    0x0033FF50: 'Ranged',   # 射撃
    0x00340EE8: 'Ranged',   # 射撃
    0x003410D8: 'Ranged',   # 射撃
    0x00343398: 'Ranged',   # 射撃
    0x00345298: 'Ranged',   # 射撃
    0x003470B0: 'Ranged',   # 射撃
    0x003473B8: 'Ranged',   # 射撃
    0x0033FF40: 'Skill',   # 技量
    0x00340ED8: 'Skill',   # 技量
    0x003410E8: 'Skill',   # 技量
    0x003433A8: 'Skill',   # 技量
    0x003452A0: 'Skill',   # 技量
    0x003470A0: 'Skill',   # 技量
    0x003473C0: 'Skill',   # 技量
    0x0033FF58: 'Defense',   # 防御
    0x00340EF0: 'Defense',   # 防御
    0x003410E0: 'Defense',   # 防御
    0x00342558: 'Defense',   # 防御
    0x003433A0: 'Defense',   # 防御
    0x003452A8: 'Defense',   # 防御
    0x003470B8: 'Defense',   # 防御
    0x003473C8: 'Defense',   # 防御
    0x0033E3D8: 'Evade',   # 回避
    0x0033FF48: 'Evade',   # 回避
    0x00340EE0: 'Evade',   # 回避
    0x003410F0: 'Evade',   # 回避
    0x00342550: 'Evade',   # 回避
    0x003433B0: 'Evade',   # 回避
    0x003452B0: 'Evade',   # 回避
    0x003470A8: 'Evade',   # 回避
    0x003473D0: 'Evade',   # 回避
    0x0033FF60: 'Hit',   # 命中
    0x00340EF8: 'Hit',   # 命中
    0x003410F8: 'Hit',   # 命中
    0x003433B8: 'Hit',   # 命中
    0x003452B8: 'Hit',   # 命中
    0x003456B8: 'Hit',   # 命中
    0x003470C0: 'Hit',   # 命中
    0x003473D8: 'Hit',   # 命中
    0x00343C10: 'Def%',   # 防御率
    0x00345F28: 'Def%',   # 防御率
    0x00343C18: 'Evade%',   # 回避率
    0x00345F30: 'Evade%',   # 回避率
    0x00343AC0: 'Stats',   # 能力
    0x003446B8: 'Stats',   # 能力
    0x00345418: 'Stats',   # 能力
    0x00346D18: 'Stats',   # 能力
    0x00341208: 'Stats',   # 能力値
    0x003473E0: 'Stats1',   # 能力１
    0x00347410: 'Stats2',   # 能力２
    0x003426D8: 'Will',   # 気力
    0x00342D28: 'Will',   # 気力
    0x00343198: 'Will',   # 気力
    0x00343C80: 'Will',   # 気力
    0x00343E98: 'Will',   # 気力
    0x003450F8: 'Will',   # 気力
    0x00345280: 'Will',   # 気力
    0x00346048: 'Will',   # 気力
    0x00342D50: 'Kills',   # 撃墜数
    0x003453F8: 'Kills',   # 撃墜数
    0x003473F8: 'Kills',   # 撃墜数
    0x0033FF68: 'Skills',   # 特殊スキル
    0x00343360: 'Skills',   # 特殊スキル
    0x003449F8: 'Skills',   # 特殊スキル
    0x00345420: 'Skills',   # 特殊スキル
    0x00346258: 'Skills',   # 特殊スキル
    0x00346820: 'Skills',   # 特殊スキル
    0x00346980: 'Skills',   # 特殊スキル
    0x003470C8: 'Skills',   # 特殊スキル
    0x00347440: 'Skills',   # 特殊スキル
    0x0033FF88: 'Spirits',   # 精神コマンド
    0x00343370: 'Spirits',   # 精神コマンド
    0x00343E28: 'Spirits',   # 精神コマンド
    0x00344678: 'Spirits',   # 精神コマンド
    0x00344998: 'Spirits',   # 精神コマンド
    0x00346248: 'Spirits',   # 精神コマンド
    0x00346800: 'Spirits',   # 精神コマンド
    0x00346970: 'Spirits',   # 精神コマンド
    0x003470E0: 'Spirits',   # 精神コマンド
    0x00347468: 'Spirits',   # 精神コマンド
    0x00345430: 'Spirits／ＳＰ',   # 精神コマンド／ＳＰ
    0x00344A18: 'Leader Bonus',   # 隊長効果
    0x00345350: 'Leader Bonus',   # 隊長効果
    0x00345EE8: 'Leader Bonus',   # 隊長効果
    0x00346268: 'Leader Bonus',   # 隊長効果
    0x00346840: 'Leader Bonus',   # 隊長効果
    0x00346990: 'Leader Bonus',   # 隊長効果
    0x00342F20: 'Leader Atk',   # 隊長攻撃力
    0x0033D9E0: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00340088: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x003401F8: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00340378: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x003404D8: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00340638: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00340F00: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00341548: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x003452E8: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00345658: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x003479B8: 'Air Gnd Sea Spc',   # 空　陸　海　宇
    0x00347400: 'Terrain',   # 空陸海宇
    0x0033D978: 'All：Ａ',   # 空陸海宇Ａ
    0x0033D988: 'All：Ｓ',   # 空陸海宇Ｓ
    0x0033D820: 'Air',   # 空
    0x00340150: 'Air',   # 空
    0x003402D0: 'Air',   # 空
    0x00340420: 'Air',   # 空
    0x00340580: 'Air',   # 空
    0x00341100: 'Air',   # 空
    0x003412D0: 'Air',   # 空
    0x00341478: 'Air',   # 空
    0x00342EF8: 'Air',   # 空
    0x003451D8: 'Air',   # 空
    0x00345C18: 'Air',   # 空
    0x00345E00: 'Air',   # 空
    0x003465A0: 'Air',   # 空
    0x003474C0: 'Air',   # 空
    0x00347910: 'Air',   # 空
    0x0033D828: 'Gnd',   # 陸
    0x00340158: 'Gnd',   # 陸
    0x003402D8: 'Gnd',   # 陸
    0x00340428: 'Gnd',   # 陸
    0x00340588: 'Gnd',   # 陸
    0x00341108: 'Gnd',   # 陸
    0x003412D8: 'Gnd',   # 陸
    0x00341480: 'Gnd',   # 陸
    0x00342F00: 'Gnd',   # 陸
    0x003451E8: 'Gnd',   # 陸
    0x00345C20: 'Gnd',   # 陸
    0x00345E08: 'Gnd',   # 陸
    0x003465A8: 'Gnd',   # 陸
    0x003474C8: 'Gnd',   # 陸
    0x00347918: 'Gnd',   # 陸
    0x0033D830: 'Sea',   # 海
    0x00341110: 'Sea',   # 海
    0x00341118: 'Spc',   # 宇
    0x003401D0: 'Air-use',   # 空専用
    0x00340350: 'Air-use',   # 空専用
    0x003404B0: 'Air-use',   # 空専用
    0x00340610: 'Air-use',   # 空専用
    0x00341528: 'Air-use',   # 空専用
    0x003436D0: 'Air-use',   # 空専用
    0x00344838: 'Air-use',   # 空専用
    0x00345E30: 'Air-use',   # 空専用
    0x00347990: 'Air-use',   # 空専用
    0x0033D7C8: 'Move',   # 移動
    0x0033E490: 'Move',   # 移動
    0x0033EE70: 'Move',   # 移動
    0x0033FEF8: 'Move',   # 移動
    0x00340048: 'Move',   # 移動
    0x003400F0: 'Move',   # 移動
    0x00340270: 'Move',   # 移動
    0x003403C0: 'Move',   # 移動
    0x00340520: 'Move',   # 移動
    0x003412C8: 'Move',   # 移動
    0x00341420: 'Move',   # 移動
    0x00342E08: 'Move',   # 移動
    0x003431A0: 'Move',   # 移動
    0x00343668: 'Move',   # 移動
    0x00343A28: 'Move',   # 移動
    0x00343C68: 'Move',   # 移動
    0x00343E80: 'Move',   # 移動
    0x003452C8: 'Move',   # 移動
    0x00345C10: 'Move',   # 移動
    0x00345ED0: 'Move',   # 移動
    0x00346758: 'Move',   # 移動
    0x00347558: 'Move',   # 移動
    0x003478B0: 'Move',   # 移動
    0x00346B60: 'Move',   # 移動力
    0x0033D7E0: 'Armor',   # 装甲
    0x0033EE40: 'Armor',   # 装甲
    0x0033F1B0: 'Armor',   # 装甲
    0x0033F800: 'Armor',   # 装甲
    0x0033FF00: 'Armor',   # 装甲
    0x00340050: 'Armor',   # 装甲
    0x00340118: 'Armor',   # 装甲
    0x00340298: 'Armor',   # 装甲
    0x003403E8: 'Armor',   # 装甲
    0x00340548: 'Armor',   # 装甲
    0x003412F8: 'Armor',   # 装甲
    0x00341448: 'Armor',   # 装甲
    0x003427D8: 'Armor',   # 装甲
    0x003452D0: 'Armor',   # 装甲
    0x00346780: 'Armor',   # 装甲
    0x00347580: 'Armor',   # 装甲
    0x003478D8: 'Armor',   # 装甲
    0x0033D7F0: 'Aim',   # 照準値
    0x0033EE50: 'Aim',   # 照準値
    0x0033F1C0: 'Aim',   # 照準値
    0x0033F810: 'Aim',   # 照準値
    0x0033FF10: 'Aim',   # 照準値
    0x00340060: 'Aim',   # 照準値
    0x00340128: 'Aim',   # 照準値
    0x003402A8: 'Aim',   # 照準値
    0x003403F8: 'Aim',   # 照準値
    0x00340558: 'Aim',   # 照準値
    0x00341458: 'Aim',   # 照準値
    0x003452E0: 'Aim',   # 照準値
    0x00346B50: 'Aim',   # 照準値
    0x003478E8: 'Aim',   # 照準値
    0x00341460: 'Size',   # サイズ
    0x0033D770: 'Parts',   # 強化パーツ
    0x0033FF28: 'Parts',   # 強化パーツ
    0x00340078: 'Parts',   # 強化パーツ
    0x00340D30: 'Parts',   # 強化パーツ
    0x00342FF0: 'Parts',   # 強化パーツ
    0x00343D18: 'Parts',   # 強化パーツ
    0x00343DE8: 'Parts',   # 強化パーツ
    0x003453D8: 'Parts',   # 強化パーツ
    0x00346D58: 'Parts',   # 強化パーツ
    0x00346DF8: 'Parts',   # 強化パーツ
    0x0033FF18: 'Abilities',   # 特殊能力
    0x00340068: 'Abilities',   # 特殊能力
    0x00341398: 'Abilities',   # 特殊能力
    0x00344A50: 'Abilities',   # 特殊能力
    0x003453E8: 'Abilities',   # 特殊能力
    0x00346278: 'Abilities',   # 特殊能力
    0x003467F0: 'Abilities',   # 特殊能力
    0x003469A0: 'Abilities',   # 特殊能力
    0x003475F0: 'Abilities',   # 特殊能力
    0x0033D810: 'Terrain',   # 地形適応
    0x00345618: 'Terrain',   # 地形適応
    0x0033EE58: 'Weapon',   # 武器
    0x0033F1C8: 'Weapon',   # 武器
    0x0033F818: 'Weapon',   # 武器
    0x003455E0: 'Ammo',   # 弾数
    0x003456D8: 'Ammo',   # 弾数
    0x0033D7F8: 'Range',   # 射程
    0x003456B0: 'Range',   # 射程
    0x0033F878: 'Type',   # 属性
    0x00345680: 'Type',   # 属性
    0x0033F830: 'Funds',   # 資金
    0x003435A0: 'Funds',   # 資金
    0x00343B80: 'Funds',   # 資金
    0x00344C98: 'Funds',   # 資金
    0x00347810: 'Funds',   # 資金
    0x00343320: 'EXP',   # 経験値
})

ELF_UI.update({
    0x0033D7E8: "Agility",   # 運動性
    0x0033EE48: "Agility",   # 運動性
    0x0033F1B8: "Agility",   # 運動性
    0x0033F808: "Agility",   # 運動性
    0x0033FF08: "Agility",   # 運動性
    0x00340058: "Agility",   # 運動性
    0x00340120: "Agility",   # 運動性
    0x003402A0: "Agility",   # 運動性
    0x003403F0: "Agility",   # 運動性
    0x00340550: "Agility",   # 運動性
    0x00341450: "Agility",   # 運動性
    0x003452D8: "Agility",   # 運動性
    0x00346B48: "Agility",   # 運動性
    0x003478E0: "Agility",   # 運動性
})

# --- SRW30-convention abbreviations (override earlier labels) ---
ELF_UI.update({
    0x0033FF38: 'CQB',   # 格闘
    0x00340ED0: 'CQB',   # 格闘
    0x003410D0: 'CQB',   # 格闘
    0x00343390: 'CQB',   # 格闘
    0x00345290: 'CQB',   # 格闘
    0x00347098: 'CQB',   # 格闘
    0x003473B0: 'CQB',   # 格闘
    0x0033FF50: 'RNG',   # 射撃
    0x00340EE8: 'RNG',   # 射撃
    0x003410D8: 'RNG',   # 射撃
    0x00343398: 'RNG',   # 射撃
    0x00345298: 'RNG',   # 射撃
    0x003470B0: 'RNG',   # 射撃
    0x003473B8: 'RNG',   # 射撃
    0x0033FF40: 'SKL',   # 技量
    0x00340ED8: 'SKL',   # 技量
    0x003410E8: 'SKL',   # 技量
    0x003433A8: 'SKL',   # 技量
    0x003452A0: 'SKL',   # 技量
    0x003470A0: 'SKL',   # 技量
    0x003473C0: 'SKL',   # 技量
    0x0033FF58: 'DEF',   # 防御
    0x00340EF0: 'DEF',   # 防御
    0x003410E0: 'DEF',   # 防御
    0x00342558: 'DEF',   # 防御
    0x003433A0: 'DEF',   # 防御
    0x003452A8: 'DEF',   # 防御
    0x003470B8: 'DEF',   # 防御
    0x003473C8: 'DEF',   # 防御
    0x0033E3D8: 'EVD',   # 回避
    0x0033FF48: 'EVD',   # 回避
    0x00340EE0: 'EVD',   # 回避
    0x003410F0: 'EVD',   # 回避
    0x00342550: 'EVD',   # 回避
    0x003433B0: 'EVD',   # 回避
    0x003452B0: 'EVD',   # 回避
    0x003470A8: 'EVD',   # 回避
    0x003473D0: 'EVD',   # 回避
    0x0033FF60: 'ACC',   # 命中
    0x00340EF8: 'ACC',   # 命中
    0x003410F8: 'ACC',   # 命中
    0x003433B8: 'ACC',   # 命中
    0x003452B8: 'ACC',   # 命中
    0x003456B8: 'ACC',   # 命中
    0x003470C0: 'ACC',   # 命中
    0x003473D8: 'ACC',   # 命中
    0x003426D8: 'Morale',   # 気力
    0x00342D28: 'Morale',   # 気力
    0x00343198: 'Morale',   # 気力
    0x00343C80: 'Morale',   # 気力
    0x00343E98: 'Morale',   # 気力
    0x003450F8: 'Morale',   # 気力
    0x00345280: 'Morale',   # 気力
    0x00346048: 'Morale',   # 気力
    0x0033D7F0: 'Sight',   # 照準値
    0x0033EE50: 'Sight',   # 照準値
    0x0033F1C0: 'Sight',   # 照準値
    0x0033F810: 'Sight',   # 照準値
    0x0033FF10: 'Sight',   # 照準値
    0x00340060: 'Sight',   # 照準値
    0x00340128: 'Sight',   # 照準値
    0x003402A8: 'Sight',   # 照準値
    0x003403F8: 'Sight',   # 照準値
    0x00340558: 'Sight',   # 照準値
    0x00341458: 'Sight',   # 照準値
    0x003452E0: 'Sight',   # 照準値
    0x00346B50: 'Sight',   # 照準値
    0x003478E8: 'Sight',   # 照準値
    0x0033D830: 'Wtr',   # 海
    0x00341110: 'Wtr',   # 海
    0x0033D828: 'Grd',   # 陸
    0x00340158: 'Grd',   # 陸
    0x003402D8: 'Grd',   # 陸
    0x00340428: 'Grd',   # 陸
    0x00340588: 'Grd',   # 陸
    0x00341108: 'Grd',   # 陸
    0x003412D8: 'Grd',   # 陸
    0x00341480: 'Grd',   # 陸
    0x00342F00: 'Grd',   # 陸
    0x003451E8: 'Grd',   # 陸
    0x00345C20: 'Grd',   # 陸
    0x00345E08: 'Grd',   # 陸
    0x003465A8: 'Grd',   # 陸
    0x003474C8: 'Grd',   # 陸
    0x00347918: 'Grd',   # 陸
    0x0033D9E0: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00340088: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x003401F8: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00340378: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x003404D8: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00340638: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00340F00: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00341548: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x003452E8: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00345658: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x003479B8: 'Air Grd Wtr Spc',   # 空　陸　海　宇
    0x00343C10: 'DEF%',   # 防御率
    0x00345F28: 'DEF%',   # 防御率
    0x00343C18: 'EVD%',   # 回避率
    0x00345F30: 'EVD%',   # 回避率
})

# --- user feedback: terrain kanji stay Japanese; Agility -> Agi ---
for _off in [0x0033D820, 0x0033D828, 0x0033D830, 0x0033D958, 0x0033D978, 0x0033D988, 0x0033D9E0, 0x00340088, 0x00340150, 0x00340158, 0x003401F8, 0x003402D0, 0x003402D8, 0x00340378, 0x00340420, 0x00340428, 0x003404D8, 0x00340580, 0x00340588, 0x00340638, 0x00340F00, 0x00341100, 0x00341108, 0x00341110, 0x00341118, 0x003412D0, 0x003412D8, 0x00341478, 0x00341480, 0x00341548, 0x00342EF8, 0x00342F00, 0x003451D8, 0x003451E8, 0x003452E8, 0x00345658, 0x00345C18, 0x00345C20, 0x00345E00, 0x00345E08, 0x003465A0, 0x003465A8, 0x00347400, 0x003474C0, 0x003474C8, 0x00347910, 0x00347918, 0x003479B8]:
    ELF_UI.pop(_off, None)
ELF_UI.update({
    0x0033D7E8: "Agi",   # 運動性
    0x0033EE48: "Agi",   # 運動性
    0x0033F1B8: "Agi",   # 運動性
    0x0033F808: "Agi",   # 運動性
    0x0033FF08: "Agi",   # 運動性
    0x00340058: "Agi",   # 運動性
    0x00340120: "Agi",   # 運動性
    0x003402A0: "Agi",   # 運動性
    0x003403F0: "Agi",   # 運動性
    0x00340550: "Agi",   # 運動性
    0x00341450: "Agi",   # 運動性
    0x003452D8: "Agi",   # 運動性
    0x00346B48: "Agi",   # 運動性
    0x003478E0: "Agi",   # 運動性
})

# --- fit 2-kanji-wide fields: Will / Stat ---
ELF_UI.update({
    0x003426D8: 'Will',   # 気力
    0x00342D28: 'Will',   # 気力
    0x00343198: 'Will',   # 気力
    0x00343C80: 'Will',   # 気力
    0x00343E98: 'Will',   # 気力
    0x003450F8: 'Will',   # 気力
    0x00345280: 'Will',   # 気力
    0x00346048: 'Will',   # 気力
    0x00343AC0: 'Stat',   # 能力
    0x003446B8: 'Stat',   # 能力
    0x00345418: 'Stat',   # 能力
    0x00346D18: 'Stat',   # 能力
})

# --- mech/weapon/map screens label batch ---
ELF_UI.update({
    0x0033F1D8: 'Squad',   # 小隊
    0x0033F848: 'Squad',   # 小隊
    0x0033FED0: 'Squad',   # 小隊
    0x00340020: 'Squad',   # 小隊
    0x00340328: 'Squad',   # 小隊
    0x00340488: 'Squad',   # 小隊
    0x003405D8: 'Squad',   # 小隊
    0x003409A0: 'Squad',   # 小隊
    0x003409C0: 'Squad',   # 小隊
    0x00340A08: 'Squad',   # 小隊
    0x00340EC0: 'Squad',   # 小隊
    0x003412A8: 'Squad',   # 小隊
    0x00342348: 'Squad',   # 小隊
    0x00342CD0: 'Squad',   # 小隊
    0x00343DF8: 'Squad',   # 小隊
    0x00344960: 'Squad',   # 小隊
    0x003453B8: 'Squad',   # 小隊
    0x00345C08: 'Squad',   # 小隊
    0x00346540: 'Squad',   # 小隊
    0x00346720: 'Squad',   # 小隊
    0x00347088: 'Squad',   # 小隊
    0x00347110: 'Squad',   # 小隊
    0x003473A0: 'Squad',   # 小隊
    0x00347520: 'Squad',   # 小隊
    0x00347968: 'Squad',   # 小隊
    0x003453D0: 'Type',   # タイプ
    0x0033F868: 'Weapon',   # 武器名
    0x003456A0: 'Weapon',   # 武器名
    0x0033F870: 'Class',   # 種別
    0x00345678: 'Class',   # 種別
    0x0033F880: 'Power',   # 攻撃力
    0x003427C8: 'Power',   # 攻撃力
    0x003456A8: 'Power',   # 攻撃力
    0x003456D0: 'Power',   # 攻撃力
    0x003455E8: 'EN Cost',   # 消費ＥＮ
    0x003455F8: 'Req Will',   # 必要気力
    0x00345608: 'Req Skill',   # 必要スキル
    0x00345628: 'Effect 1',   # 特殊効果１
    0x00345638: 'Effect 2',   # 特殊効果２
    0x0033D800: 'Effect',   # 特殊効果
    0x00345648: 'Upgrades',   # 改造段階
    0x00345F38: 'HP Regen',   # ＨＰ回復
    0x00345F48: 'EN Regen',   # ＥＮ回復
    0x00345EB8: 'No Change',   # 変化無し
    0x00343AB8: 'Spirit',   # 精神
    0x0033EE58: 'Weapon',   # 武器
    0x0033F1C8: 'Weapon',   # 武器
    0x0033F818: 'Weapon',   # 武器
    0x0033D798: 'Terrain',   # 地形
    0x003401B0: 'Terrain',   # 地形
})

# --- batch 2: skill & spirit names + descriptions ---
from ui_batch2 import BATCH as _B2
ELF_UI.update(_B2)

# --- unit names (akurasu official romanizations) ---
ELF_UI.update({
    0x0033A110: 'Great Mazinger',   # グレートマジンガー
    0x0033A260: 'Turn A Gundam',   # ∀ガンダム
    0x00340A68: 'Orguss',   # オーガス
    0x00340A78: 'Ishkick',   # イシュキック
    0x00340A88: 'Nikick',   # ナイキック
    0x00340AF0: 'ZAKU Warrior',   # ザクウォーリア
    0x00340B60: 'Nirvash',   # ニルヴァーシュ
    0x00340B70: 'Virgola',   # バルゴラ
    0x00340B80: 'SUMO',   # スモー
    0x00340BA0: 'Gundam Double X',   # ガンダムダブルエックス
    0x003479E0: 'Gunleon',   # ガンレオン
    0x00347A00: 'Virgola',   # バルゴラ
})

# --- batch 3: intermission UI ---
from ui_batch3 import BATCH as _B3
ELF_UI.update(_B3)

# --- batches 4-6: system msgs, battle prep, map UI ---
from ui_batch4 import BATCH as _B4
ELF_UI.update(_B4)
from ui_batch5 import BATCH as _B5
ELF_UI.update(_B5)
from ui_batch6 import BATCH as _B6
ELF_UI.update(_B6)

# --- batch 7: options/search/library/QA ---
from ui_batch7 import BATCH as _B7
ELF_UI.update(_B7)

# --- batch 8: bazaar item descriptions ---
from ui_batch8 import BATCH as _B8
ELF_UI.update(_B8)

# --- batch 9: library/viewer/confirm msgs ---
from ui_batch9 import BATCH as _B9
ELF_UI.update(_B9)

# --- batch 10: overlap fixes + control-code strings ---
from ui_batch10 import BATCH as _B10
ELF_UI.update(_B10)
ELF_UI.update({  # WIL abbreviation (forecast field is 3 chars wide)
    0x003426D8: "WIL",
    0x00342D28: "WIL",
    0x00343198: "WIL",
    0x00343C80: "WIL",
    0x00343E98: "WIL",
    0x003450F8: "WIL",
    0x00345280: "WIL",
    0x00346048: "WIL",
})
