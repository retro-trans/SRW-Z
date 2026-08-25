# -*- coding: utf-8 -*-
"""SR Point conditions and the mission objectives the first extraction missed.

The original objective sweep only caught the Victory/Defeat lines, so the
"SR Point condition" box stayed Japanese on every stage - including the very
common 'なし' ("None"), which alone appears in 47 places.

Names follow analysis/name_source.json so these match the unit list and
dialogue (Adette, Rushrod, Kragen, Gekko-Goh, Dogozzo, Shurouga...).

Budgets are BYTES after menu encoding, where every digit and full stop becomes
FULLWIDTH and costs 2 - see zkn_build/apply_stage. sr_apply.py checks each one.
"""

SR_EN = {
    'なし':
        'None',

    'クワトロ、またはカミーユのＨＰを４０００以下にする。':
        "Reduce Quattro's or Kamille's HP to\n4000 or less.",

    'クワトロ、またはカミーユを撃墜する。\n（両者はＨＰ４０００以下で撤退する）':
        'Shoot down Quattro or Kamille. (Both\nretreat at 4000 HP or less.)',

    'アレキサンドリアのＨＰを１００００以下にする。':
        "Reduce Alexandria's HP to 10000 or\nless.",

    '４ターン以内にイアンを撃墜する。または４ターン以内にスティング、\nアウル、ステラを撃墜し、最後にネオを撃墜する。':
        'Shoot down Ian within 4 turns, or shoot\ndown Sting, Auel and Stellar within 4\nturns, then Neo last.',

    'アデットのドゴッゾを撃墜する。\nなお、アデット機はＨＰ３０００以下で後退する。':
        "Shoot down Adette's Dogozzo. (Adette\nretreats at 3000 HP or less.)",

    '５ターン味方フェイズ以内に全ての敵を撃墜し、\n最後にラッシュロッドを撃墜する。':
        'Within 5 ally phases shoot down all\nenemies, then Rushrod last.',

    '登場から３ターン以内に全てのアーキタイプを撃墜し、\n最後にマミーを撃墜する。':
        'Within 3 turns of appearing, shoot down\nall Archetypes, then Mummy last.',

    '月光号のＨＰを１０％以下にする。':
        'Reduce Gekko-Goh HP to 10% or less.',

    'クラーゲンを４機以上、撃墜する。\nまたはクラーゲン全機がマップ端に達する前に\nテラルを撃墜する。':
        'Shoot down 4 or more Kragen, or shoot\ndown Teraru before every Kragen reaches\nthe map edge.',

    'ソレイユがマップ端に到達する前に他の敵を全滅させ、\n最後にエルダー戦艦を撃墜する。':
        'Destroy all other enemies before Soleil\nreaches the map edge, then the Elder\nwarship.',

    'ガルダ級のＨＰを２０００以下にする。':
        'Reduce Garuda-class HP to 2000 or\nless.',

    '６ターン以内に他の敵を全て撃墜した後、\nニルヴァーシュ\u3000ｔｈｅ\u3000ＥＮＤを撃墜する。':
        'Within 6 turns shoot down all other\nenemies, then Nirvash the END.',

    'オルソン・アテナ・ジロン・ゲイン・ロジャー・チャールズ、\nいずれかの撃墜。':
        'Shoot down any of Olson, Athena, Jiron,\nGain, Roger or Charles.',

    '６ターン以内に他の敵を全て撃墜した後、\n最後にデストロイガンダムを撃墜する。':
        'Within 6 turns shoot down all other\nenemies, then the Destroy Gundam last.',

    '３ターン以内にシャギアとオルバを撃墜する\n（両者はＨＰ８０００以下で撤退する）。':
        'Shoot down Shagia and Olba within 3\nturns. (Both retreat at 8000 HP.)',

    'カオス・レオー、カオス・アングイス、\nカオス・カペル、シュロウガ、いずれかの撃墜。':
        'Shoot down any of Chaos Leo, Chaos\nAnguis, Chaos Capel or Shurouga.',

    'アクエリオンアルファ、ケルビム・イスキューロン、\nケルビムマーズのいずれかと、メカ要塞鬼の撃墜。':
        'Shoot down Mecha Yosaiki and any of\nAquarion Alpha, Cherubim Ischyron or\nCherubim Mars.',

    'アクエリオンアルファ、ケルビム・イスキューロン、\nケルビムマーズのいずれかの撃墜。':
        'Shoot down any of Aquarion Alpha,\nCherubim Ischyron or Cherubim Mars.',

}
