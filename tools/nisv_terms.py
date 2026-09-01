# -*- coding: utf-8 -*-
"""The UI vocabulary rec6's cross-reference lists are built from.

rec6's help pages end with a "see also" line of glossary terms in fullwidth
angle brackets - 233 distinct terms, 397 references. They are NOT free prose:
each one names something the player sees elsewhere in the game, so inventing a
wording here would contradict the menus.

WHERE EACH ENGLISH FORM COMES FROM, in order of authority:

  1. analysis/compdata_pairs.json - a real japanese->english pair table
     (Spirits, Parts, Terrain, Skills, Abilities, Shield, Repair Module,
     Resupply Module, Tri Formation, Wide Formation, Melee, Sword, Leader,
     Squad Bonus, Booster, Mega Booster ...)
  2. Strings already shipped in COMPDATA, confirmed by searching the image:
     Support Def, Tri Charge, Pilot Training, Blocking, Shield Defend, Valor,
     Soul, Wall, Spirit, Sense, Counter, Re-Attack, Size, Armor, Mobility,
     Accuracy, Squad Move, Refit, Barrier Pierce.
  3. The ability descriptions, where the japanese and english runs sit in the
     same order and pair by position: 加速 Accel, 覚醒 Awaken, 必中 Strike,
     ひらめき Alert, 集中 Focus, 気力 Will, 運動性 Mobility, 照準値 Accuracy,
     装甲値 Armor.
  4. Only where the game ships no english at all, this file decides - and then
     it follows what help_shorten.py already wrote for the DATA HELP panels,
     so the two agree.

DO NOT paste offsets from the japanese COMPDATA against the english one to
extend this: COMPDATA has been repacked, the offsets no longer correspond, and
that method produced pure garbage when it was tried here.

Terms with no entry are left alone, and any cross-reference line containing
one stays japanese rather than going out half-translated.
"""

# japanese -> english, as the rest of the game words it
TERMS = {
 # formations and squads
 u"フォーメーション": u"Formation",
 u"トライ・フォーメーション": u"Tri Formation",
 u"センター・フォーメーション": u"Center Formation",
 u"ワイド・フォーメーション": u"Wide Formation",
 u"フォーメーションの相性": u"Formation Matchups",
 u"小隊": u"Squad",
 u"小隊攻撃": u"Squad Atk",
 u"小隊移動力": u"Squad Move",
 u"小隊移動タイプ": u"Squad Move Type",
 u"小隊ボーナス": u"Squad Bonus",
 u"隊長効果": u"Leader",
 u"トライチャージ": u"Tri Charge",
 u"バリア広域化": u"Squad Barrier",
 u"全体攻撃": u"All Atk",
 # movement
 u"移動力": u"Move",
 u"移動タイプ": u"Move Type",
 u"移動コスト": u"Move Cost",
 u"空": u"Air",
 u"陸": u"Land",
 u"水": u"Water",
 u"加速": u"Accel",
 u"迅速": u"Rush",
 u"ブースター": u"Booster",
 u"メガブースター": u"Mega Booster",
 u"ミノフスキークラフト": u"Minovsky Craft",
 u"防塵装置": u"Dust Filter",
 u"スクリューモジュール": u"Screw Module",
 # attack
 u"攻撃": u"Attack",
 u"通常攻撃": u"Normal Atk",
 u"攻撃方法": u"Attack Type",
 u"攻撃力": u"Attack",
 u"援護攻撃": u"Support Atk",
 u"援護防御": u"Support Def",
 u"反撃": u"Counter",
 u"連携攻撃": u"Combo Atk",
 u"支援攻撃": u"Assist Atk",
 u"集束攻撃": u"Focused Atk",
 u"ＴＲＩ兵器": u"TRI weapon",
 u"ＰＬＡ武器": u"PLA weapon",
 u"ＭＡＰ兵器": u"MAP weapon",
 u"特殊効果": u"Special Effect",
 u"属性": u"Attribute",
 u"バリア貫通": u"Barrier Pierce",
 u"サイズ補正無視": u"Ignore Size",
 u"装甲値ダウン": u"Armor Down",
 u"運動性ダウン": u"Mobility Down",
 u"照準値ダウン": u"Accuracy Down",
 u"プレースメント修正": u"Placement Bonus",
 u"連続ターゲット補正": u"Repeat Target Bonus",
 u"敵味方識別": u"IFF",
 u"反撃不能": u"No Counter",
 # damage and defence
 u"防御": u"Defend",
 u"防御力": u"Defence",
 u"装甲": u"Armor",
 u"ＨＰ": u"HP",
 u"ＥＮ": u"EN",
 u"ＳＰ": u"SP",
 u"撃墜": u"Shot Down",
 u"敗北条件": u"Defeat Conditions",
 u"ゲームオーバー": u"Game Over",
 u"ブロッキング": u"Blocking",
 u"シールド防御": u"Shield Defend",
 u"ガード": u"Guard",
 u"盾装備": u"Shield",
 u"剣装備": u"Sword",
 u"チョバムアーマー": u"Chobham Armor",
 u"ハイブリッドアーマー": u"Hybrid Armor",
 u"ナノスキンアーマー": u"Nanoskin Armor",
 u"不屈": u"Guts",
 u"鉄壁": u"Wall",
 u"気合": u"Spirit",
 # hit and evade
 u"命中": u"Hit",
 u"最終命中率": u"Final Hit Rate",
 u"回避": u"Evade",
 u"最終回避率": u"Final Evade Rate",
 u"回避方法": u"Evade Method",
 u"見切り": u"Sense",
 u"必中": u"Strike",
 u"集中": u"Focus",
 u"ひらめき": u"Alert",
 u"照準値": u"Accuracy",
 u"運動性": u"Mobility",
 u"サイズ": u"Size",
 u"攻撃対象のサイズ": u"Target Size",
 u"攻撃相手との距離": u"Range to Target",
 u"敵との距離": u"Range to Enemy",
 u"地形適応": u"Terrain",
 u"地形効果": u"Terrain Effect",
 u"ＶＲメット": u"VR Helmet",
 u"感応ヘルメット": u"Psycho Helmet",
 u"マグネットコーティング": u"Magnet Coating",
 u"慣性制御システム": u"Inertia Control",
 # will
 u"気力": u"Will",
 u"気迫": u"Vigor",
 u"激励": u"Cheer",
 u"闘争心": u"Fighting Spirit",
 u"戦意高揚": u"Morale Boost",
 u"気力限界突破": u"Will Limit Break",
 u"エースパイロット": u"Ace Pilot",
 u"トップエース": u"Top Ace",
 u"熱血": u"Valor",
 u"魂": u"Soul",
 u"直撃": u"Direct Hit",
 u"覚醒": u"Awaken",
 # growth and shop
 u"精神コマンド": u"Spirits",
 u"パイロット養成": u"Pilot Training",
 u"能力値上昇": u"Stat Growth",
 u"特殊スキル修得": u"Skill Learning",
 u"機体改造": u"Unit Upgrade",
 u"武器改造": u"Weapon Upgrade",
 u"武器の選択": u"Weapon Choice",
 u"強化パーツ": u"Parts",
 u"機体換装": u"Refit",
 u"バザー": u"Bazaar",
 u"資金": u"Funds",
 u"経験値": u"EXP",
 u"格闘": u"Melee",
 u"射撃": u"Ranged",
 u"特殊能力": u"Abilities",
 u"特殊スキル": u"Skills",
 u"修理装置": u"Repair Module",
 u"補給装置": u"Resupply Module",
 u"修理技能": u"Repair Skill",
 u"補給技能": u"Resupply Skill",
 u"隊長ボーナス": u"Leader Bonus",
 u"ＨＰ回復": u"HP Regen",
 u"ＥＮ回復": u"EN Regen",
 u"補給": u"Resupply",
 u"搭載": u"Load",
 u"回収": u"Recover",
 u"性格": u"Personality",
 u"難易度": u"Difficulty",
}
