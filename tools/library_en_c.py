# -*- coding: utf-8 -*-
"""Library / help database, batch 3: list sort orders, mission conditions,
battle-map status and combat action labels."""

LIBRARY_EN_C = {
    491360: "Sorts by current SP, desc.",
    491392: "The spirit commands the pilot has learned.",
    491440: "Sorts by skill level, descending.",
    491488: "Sorts by uses remaining, descending.",
    491536: "The special skills the pilot has learned.",
    491584: "Sorts by leader or captain effect order.",
    491632: "The special abilities the unit has.",
    491680: "Sorts by skill activation rate, desc.",
    491728: "Sorts by skill power, large to small.",
    491776: "The special gear needed for a squad bonus.",
    491824: "Shows which squad bonus it belongs to, in red.",
    491872: "Sorts units with a repair device first.",
    491920: "Sorts units with a resupply device first.",
    491968: "Sorts pilots who have learned Support Attack\n"
            "first, by skill level descending.",
    492064: "Sorts pilots who have learned Support Defend\n"
            "first, by skill level descending.",
    492224: "Sorts by current EN, desc.",
    492256: "Sorts by current Will, desc.",
    492288: "Sorts by PP held, desc.",
    492320: "Sorts by EXP needed to next level, desc.",
    492384: "Sorts by kills, desc.",
    492416: "Sorts by the attack power of the unit's\n"
            "strongest weapon, descending.",
    492496: "The type and traits of the unit's strongest\n"
            "weapon.",
    492560: "The main pilot aboard the unit.",
    492800: "Sorts by the squad's total current EN,\n"
            "descending.",
    492880: "Sorts by the leader's current SP, desc.",
    492928: "Sorts by the leader's current Will, desc.",
    492976: "Sorts by member 1's current SP, desc.",
    493024: "Sorts by member 1's current Will, desc.",
    493072: "Sorts by member 2's current SP, desc.",
    493120: "Sorts by member 2's current Will, desc.",
    493168: "Sorts by leader PP, desc.",
    493200: "Sorts by the leader's kills, desc.",
    493248: "Sorts by member 1's PP, desc.",
    493296: "Sorts by member 1's kills, desc.",
    493344: "Sorts by member 2's PP, desc.",
    493392: "Sorts by member 2's kills, desc.",
    493440: "Sorts by squad Move, desc.",
    493472: "For each terrain, sorts squad move type from\n"
            "passable (white) to difficult (grey) to very\n"
            "hard or impossible (blank).",
    493600: "Sorts squads with a repair device first.",
    493648: "Sorts squads with a resupply device first.",
    493696: "Sorts squads that have learned Support Attack\n"
            "first, by skill level descending.",
    493792: "Sorts squads that have learned Support Defend\n"
            "first, by skill level descending.",
    493888: "Sorts by the attack power of the leader's\n"
            "strongest weapon, descending.",
    493968: "Sorts by the PLA weapon power of member 1.",
    494032: "Sorts by the PLA weapon power of member 2.",
    494096: "Sorts by Tri Charge attack power, the average of\n"
            "the three TRI weapons, descending. Some pilot\n"
            "combinations in a squad raise Tri Charge power.",
    494272: "The conditions for ending the battle map. Meeting\n"
            "them, or the turns advancing, can trigger events\n"
            "that change them or add new ones. The objective\n"
            "screen then shows the latest conditions.",
    494496: "The conditions that cause a game over. Meeting\n"
            "them, or the turns advancing, can trigger events\n"
            "that change them or add new ones. The objective\n"
            "screen then shows the latest conditions.",
    494720: "The conditions for earning an SR Point, which\n"
            "affects difficulty. Until they can be met they\n"
            "show as ???. Even in a scenario with several\n"
            "battle maps, only 1 SR Point can be earned.",
    494960: "Turns elapsed since this battle map began.",
    495024: "Total turns elapsed since Episode 1 began.",
    495088: "Funds earned since this battle map began.",
    495152: "The total funds you currently hold.",
    495200: "BS earned since this battle map began.",
    495264: "The total BS you currently hold.",
    495312: "Whether the SR Point for this scenario has been\n"
            "earned. Shows Not Earned if not, Earned if so.",
    495440: "The number of squads each side has deployed on\n"
            "the map. Allies in blue, enemies in red.",
    495536: "How many enemy units were downed on this battle\n"
            "map. <27> opens the detailed kill list.",
    495632: "How many ally units were downed on this battle\n"
            "map. <27> opens the detailed kill list.",
    495728: "The parts obtained by downing enemies on this\n"
            "battle map.",
    495792: "Sorts by kills on this battle map, desc.",
    495840: "Sorts by repair cost owed, descending.",
    495888: "Reserve squads with <23>, then <27> to apply all.\n"
            "The red mark is normally <26>, and <25> when\n"
            "reserved. If it matches the current formation it\n"
            "becomes <29> and cannot be chosen.",
    496080: "Short codes for the current formation.\n"
            "T - Tri Formation\n"
            "C - Center Formation\n"
            "W - Wide Formation",
    496208: "Marks the side that is attacking.",
    496272: "Marks the side that is defending.",
    496336: "The formation currently selected.",
    496384: "Units joining support attack and support defend,\n"
            "with uses left and the support hit rate.",
    496496: "The unit chose a normal attack with no type\n"
            "label.",
    496560: "The unit chose to defend. Defending cuts damage\n"
            "taken to 60%. With a shield equipped it drops to\n"
            "40%. Cutting and afterimage still work while\n"
            "defending.",
    496768: "The unit chose to evade. Evading halves the\n"
            "enemy's hit rate. If the computed hit rate is\n"
            "over 100%, it will not drop to 50% but stay\n"
            "higher.",
    496960: "The unit chose to counter.",
    497008: "The unit chose to stand by.",
    497056: "The unit will attack with Tri Charge.",
    497120: "The unit will use an all-out attack.",
    497168: "The unit will use a combination attack.",
    497216: "The unit is joining a combination attack.",
    497280: "The unit will use a <35> combination attack.",
    497344: "The unit will join the squad attack.",
    497392: "For some reason, such as low Will or a range\n"
            "mismatch, the unit will not or cannot join the\n"
            "squad attack.",
    497520: "The unit will not take part in this battle.",
}
