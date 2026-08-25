# -*- coding: utf-8 -*-
"""English for the 55 ability/skill descriptions in COMPDATA 0x6B8F0..0x6D0C0.

Keyed by OFFSET (these have no row index - they are not part of the STAGE
script). Terminology matches the ELF UI work already shipped: 気力 = Will,
運動性 = Mobility, 照準値 = Accuracy, 分身 = Afterimage, 必中/ひらめき/集中/覚醒
= Strike/Alert/Focus/Awaken, 切り払い = Sword Cut, センター・フォーメーション =
Center Formation.

Budgets are roomy because Japanese costs 2 bytes/char and English 1.
"""

ABILITIES = {
    0x6B8F0: "All squad members gain +10% final\naccuracy and evasion. Works even if\n"
             "the owner is a squad member.",
    0x6B960: "All squad units gain Air movement,\nand unit/weapon Air terrain becomes A.\n"
             "Works even if the owner is a squad\nmember.",
    0x6B9E0: "Recovers 10% of max HP before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BA40: "Recovers 20% of max HP before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BAA0: "Recovers 30% of max HP before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BB00: "Recovers 10% of max EN before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BB60: "Recovers 20% of max EN before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BBC0: "Recovers 30% of max EN before your\nturn begins. Stacks with other\nrecovery effects.",
    0x6BC20: "Activates at Will 130+.\nFinal damage dealt x1.25.",
    0x6BC70: "At Will 130+, ignores terrain when\nmoving and fully evades enemy\nattacks 25% of the time.",
    0x6BCD0: "Fully recovers EN once per map.",
    0x6BD00: "Activates at Will 130+.\nThe best stats among the 3 pilots\naboard apply to the main pilot.",
    0x6BD70: "No EN cost per turn while airborne.",
    0x6BDA0: "Fully nullifies P-type effects.",
    0x6BDD0: "Fully nullifies P and R effects.",
    0x6BE00: "Can change the unit's form.",
    0x6BE30: "Can combine several units into one,\nor separate them. The units must be\nin the same squad.",
    0x6BEB0: "With a Newtype L5+ pilot aboard,\nactivates at Will 130+.\n"
             "Unit and weapon performance rises.",
    0x6BF20: "Can swap parts while Minerva is on\nthe map. A part once swapped cannot\n"
             "be swapped again on the same map.",
    0x6BF90: "At Will 130+, can combine into God\nGravion. After 3 turns the\ncombination is forcibly released;\nno recombining on this map.",
    0x6C030: "After 3 turns as God Gravion the\ncombination is forcibly released.\nRecombining on this map is\nimpossible.",
    # menu-encoded (fullwidth digits/dots) this must stay under the 111-byte
    # slot - the long form was 112 and reverted to Japanese
    0x6C0A0: "Activates at Will 130+. Fully\nevades enemy attacks. Trigger\nrate varies by ability.",
    0x6C110: "Activates at Will 130+.\nEffect varies by Overman.",
    0x6C150: "Nullifies damage of 2000 or less.\nActivates at Will 130+, costs 5 EN.\n"
             "In Center Formation, applies to all\nsquad units.",
    0x6C1E0: "Reduces damage from ranged beam\nattacks by 1000. Costs 10 EN.\n"
             "In Center Formation, applies to all\nsquad units.",
    0x6C270: "Reduces damage from ranged beam\nattacks by 1500. Activates at\n"
             "Will 110+, costs 10 EN.\nIn Center Formation, applies to all\nsquad units.",
    0x6C310: "Nullifies damage of 1500 or less.\nActivates at Will 100+, costs 10 EN.\n"
             "In Center Formation, applies to all\nsquad units.",
    0x6C3A0: "Nullifies damage of 2500 or less.\nCosts 10 EN.\n"
             "In Center Formation, applies to all\nsquad units.",
    0x6C420: "Reduces damage by 1000 + Over Sense\nL x 100. Activates at Will 110+,\n"
             "costs 5 EN. In Center Formation,\napplies to all squad units.",
    0x6C4C0: "Reduces damage by 2000.\nActivates at Will 100+, costs 5 EN.\n"
             "In Center Formation, applies to all\nsquad units.",
    0x6C550: "Reduces damage by 1000.\nCosts 10 EN. In Center Formation,\napplies to all squad units.",
    0x6C5C0: "When Defend is chosen, Shield Block\nreduces damage further than normal\n"
             "defense. If Blocking is held, the\nsame effect may trigger on Counter.",
    0x6C670: "If the pilot has the Blocking skill,\ntriggers Sword Cut, nullifying enemy\n"
             "physical attacks. Trigger rate is set\nby the skill gap.",
    0x6C710: "Fully restores EN and ammo for one\nunit in your or an adjacent squad.\n"
             "Also resupplies 10% EN to all squad\nunits at turn start. Works even if\n"
             "the owner is a squad member.",
    0x6C7C0: "Restores HP for all units in your\nor an adjacent squad. Also repairs\n"
             "10% HP to all squad units at turn\nstart. Works even if the owner is\na squad member.",
    0x6C860: "Recovers a set % of HP at turn start.",
    0x6C890: "Recovers a set % of EN at turn start.",
    0x6C8C0: "Reduces non-beam damage by 2000.\nCosts 10 EN.",
    0x6C910: "Fully nullifies ranged beam attacks.\nCosts 10 EN.",
    0x6C950: "Nullifies beam damage of 2500 or\nless. Costs 10 EN.",
    0x6C9A0: "Activates with pilot Over Sense L2+\nand Will 130+.\n"
             "Mobility/Accuracy +10 + Over Sense\nL x 1. Afterimage (30% chance).",
    0x6CA30: "Activates with pilot Over Sense L4+\nand Will 130+.\n"
             "Mobility/Accuracy +10 + Over Sense\nL x 2. Movement +1.\nAfterimage (30%).",
    0x6CAC0: "Activates with pilot Over Sense L6+\nand Will 130+.\n"
             "Mobility/Accuracy +10 + Over Sense\nL x 2. Movement +2.\nAfterimage (50%).",
    0x6CB50: "Activates with pilot Over Sense L3+\nand Will 130+.\nAccel applies each turn.\n"
             "Photon Mat barrier effect +200.",
    0x6CBD0: "Activates with pilot Over Sense L3+\nand Will 130+.\nAwaken applies each turn.\n"
             "Mobility +10 + Over Sense L x 2.",
    0x6CC50: "Activates with pilot Over Sense L3+\nand Will 130+.\n"
             "Mobility/Accuracy +10 + Over Sense\nL x 2.",
    0x6CCC0: "Activates with pilot Over Sense L2+\nand Will 130+. Mobility +10.",
    0x6CD10: "Activates with pilot Over Sense L3+\nand Will 130+. Armor +300.",
    0x6CD60: "Activates with pilot Over Sense L3+\nand Will 130+.\n"
             "Strike, Alert, Focus and Awaken\napply each turn.",
    0x6CDE0: "Activates with pilot Over Sense L3+\nand Will 130+.\n"
             "Mobility +10 + Over Sense L x 2.\nAfterimage (50% chance).",
    0x6CE60: "Activates with pilot Over Sense L2+\nand Will 130+.\nStrike applies each turn.",
    0x6CEC0: "Activates with pilot Over Sense L4+\nand Will 130+.\n"
             "Mobility +10 + Over Sense L x 2.\nAfterimage (50% chance).",
    0x6CF40: "Activates with pilot Over Sense L3+\nand Will 130+.\nMobility +10.\n"
             "Afterimage (25% chance).",
    0x6CFB0: "Activates with pilot Over Sense L5+\nand Will 130+.\n"
             "Enemy units within 5 tiles suffer\n-50% accuracy and evasion,\n-20% attack and defense.",
    0x6D060: "Activates at Will 130+.\nFully evades enemy attacks\nregardless of accuracy.\n50% chance.",
}
