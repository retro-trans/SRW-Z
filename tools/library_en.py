# -*- coding: utf-8 -*-
"""English for the Library / help database in COMPDATA (0x74000+).

Ability names, status-screen labels, and the long "what does this stat mean"
explanations reachable from the Library and from the unit/pilot screens.

Rendered on menu screens, so patch_compdata encodes these with mode "menu"
(digits and . / : ; < = become fullwidth). IMPORTANT: sequences like <0>, <15>
and [31] are BUTTON/ICON TOKENS made of those same byte values - the applier
keeps them raw and menu-encodes only the text around them.
"""

LIBRARY_EN = {
    # --- ability / category names ---
    475816: 'Subspace Dive',
    475840: 'Trinity Charge',
    475864: 'Bio-Sensor',
    475880: 'Psycoframe',
    475904: 'Element System',
    475944: 'Anti-Psychic',
    475968: 'All Canceller',
    476000: 'Graviton Crit',
    476016: 'Barriers',
    476032: 'Armor',
    476136: 'Spirits',
    476152: 'Skills',
    476168: 'Leader',
    476184: 'Abilities',
    476200: 'Squad Bonus',
    476352: 'Parts',
    # --- button hints (contain <0> icon tokens) ---
    476256: 'Press <0> for the control list.',
    476304: 'Press <0> for the Character File.',
    476368: 'Press <0> for the Robot File.',
    # --- pilot status explanations ---
    476416: "Short for Level, a guide to a pilot's strength.\n"
            "Level rises as EXP is earned, up to a max of 99.\n"
            "As level rises, stats improve and new skills and\n"
            "spirit commands are learned.",
    476640: "A number for the pilot's morale. The higher it is,\n"
            "the more damage and defense they gain, and the more\n"
            "weapon types they can use. The base is 100, varying\n"
            "from 50 to 150 with battle results.",
    476880: "Short for Pilot Points, gained by downing enemies\n"
            "or earning SR Points. Spend them to strengthen a\n"
            "pilot. Non-leaders receive only 75% of PP earned.",
    477072: "Short for Spirit Points, shown as current SP over\n"
            "max SP. Spirit commands consume them. Ways to\n"
            "recover SP on a battle map are very limited, so\n"
            "use them wisely or they run dry.",
    477312: "The EXP needed to reach the next level. Each level\n"
            "requires 500 EXP. The greater the level gap with\n"
            "the enemy, the more EXP earned.",
    477488: "Short for Experience, earned by landing an attack\n"
            "or counter and surviving, or by using repair or\n"
            "resupply. Non-leaders receive only 75%.",
    477648: "Total enemy units shot down. Only the pilot who\n"
            "reduces an enemy's HP to 0 gets the credit, not\n"
            "others in the battle. At 50 kills a pilot becomes\n"
            "an Ace and gains a <1> icon.",
    477856: "A bonus for a pilot who reaches 50 kills. Funds from\n"
            "downing enemies become 1.2x and starting Will +5.\n"
            "Funds are capped at 2x, so even with Lucky it stops\n"
            "at 2x rather than 2.4x.",
    478096: "The six pilot stats that directly affect combat -\n"
            "Melee, Ranged, Skill, Defense, Evade and Hit.\n"
            "They grow with level, but the rate depends on each\n"
            "pilot's growth type.",
    478336: "The pilot's melee attack ability. The higher it\n"
            "is, the more damage melee-class weapons deal.",
    478464: "The pilot's ranged attack ability. The higher it\n"
            "is, the more damage ranged-class weapons deal.",
    478592: "The pilot's piloting precision. The higher it is,\n"
            "the higher the critical rate, and the easier it is\n"
            "for skills judged by Skill gap to fire, such as\n"
            "Re-Attack and Blocking.",
    478768: "How well the pilot defends. The higher it is, the\n"
            "more damage from enemy attacks is reduced.",
    478896: "How well the pilot evades. The higher this plus\n"
            "the unit's Mobility, the more easily it dodges.",
    479024: "The pilot's accuracy. The higher this plus the\n"
            "unit's Sight and the weapon's hit bonus, the more\n"
            "easily attacks land.",
    479152: "The pilot's adaptation to each battle terrain,\n"
            "ranked S, A, B, C, D from best. In battle the\n"
            "unit's terrain rating, decided from pilot and unit\n"
            "ratings together, is what applies.",
    479360: "Fires only when the pilot is a squad leader, and\n"
            "applies to the whole squad. A captain's version\n"
            "is called a captain effect.",
    479504: "The various skills a pilot has learned. When a\n"
            "skill that works under set conditions activates,\n"
            "its text changes color. Reaching set levels teaches\n"
            "new skills or raises skill levels.",
    479728: "Commands that aid battle in many ways; up to five\n"
            "are learned. The status screen shows them as\n"
            "Spirit (SP cost). Using one costs that much SP.\n"
            "Effects and duration differ per command.",
    479968: "Shows which squad the unit belongs to. A single\n"
            "digit means a battleship, two digits a formed\n"
            "squad, and letters an event squad.",
    480112: "Icons showing squad information.\n"
            "<2> marks a battleship,\n"
            "<4> marks a squad leader,\n"
            "<3> marks a unit in an event squad.",
    480272: "The unit's size class, from the largest <15> down\n"
            "through <16> > <17> > <18> > <19>.\n"
            "When sizes differ, the smaller side gains hit and\n"
            "evade, the larger side gains a damage bonus.",
    480496: "The damage a unit can take; at 0 it is shot down.\n"
            "Shown as current HP over max HP, or current HP\n"
            "alone. Lost HP is restored by repair units, spirit\n"
            "commands or parts.",
    480688: "The energy a unit carries, spent using weapons and\n"
            "moving. Shown as current EN over max EN, or current\n"
            "EN alone. Lost EN is restored by resupply units,\n"
            "spirit commands or parts.",
    480896: "Armor is how tough the unit is. The higher it is,\n"
            "the less damage taken from enemies. A pilot with\n"
            "high Defense aboard uses it even better.",
    481088: "Mobility is the unit's agility. The higher this\n"
            "plus the pilot's Evade, the more easily the unit\n"
            "dodges enemy attacks.",
    481232: "Sight is the unit's accuracy. The higher this plus\n"
            "the pilot's Hit and the weapon's hit bonus, the\n"
            "more easily attacks land.",
    481392: "The unit's adaptation to each battle terrain,\n"
            "ranked S, A, B, C, D from best. In battle the\n"
            "unit's terrain rating, decided from pilot and unit\n"
            "ratings together, is what applies.",
    481584: "Move is how far a unit can travel. Normally one\n"
            "square costs 1 Move, but some terrain costs more\n"
            "for a single square. The Move needed to cross\n"
            "terrain is called the movement cost.",
    481824: "Move type is the terrain a unit can travel. If Air,\n"
            "Land or Water is listed, the unit can change to\n"
            "that element. Air-only or land-only warships\n"
            "cannot change terrain.",
    482064: "Special abilities built into the unit. Each unit\n"
            "can hold up to four. Abilities with activation\n"
            "conditions change text color while active.",
    482240: "The parts equipped to the unit. How many can be\n"
            "equipped depends on the unit's part slots, 1 to 4.\n"
            "Consumable parts vanish when used from the Parts\n"
            "command.",
    482432: "This icon lights when the unit has a repair device.\n"
            "It can use the Repair command to restore HP. Its\n"
            "squad also recovers HP at the start of each ally\n"
            "phase, 10% of max per repair unit.",
    482688: "A unit with this icon lit has a resupply device and\n"
            "can use Resupply, fully restoring EN and ammo at\n"
            "the cost of 10 Will. Its squad also recovers EN at\n"
            "ally phase start, 10% of max per unit.",
    482944: "Two kinds of barrier that spend EN to protect the\n"
            "unit. Nullify: damage within the barrier value\n"
            "becomes 0; [31] above that value it lands in full.\n"
            "Reduce [8]: damage is cut by the barrier value.",
    483184: "This icon lights when the unit has special armor.\n"
            "Like <21> it blocks enemy attacks, but it can\n"
            "cover special effects as well as damage.",
    483344: "This icon lights when the unit carries a sword.\n"
            "If the pilot has the Blocking skill, swords or\n"
            "solid-round weapons may be nullified by Cutting.\n"
            "The rate depends on the Skill difference.",
    483568: "Lights when the unit carries a shield. Choosing\n"
            "Defend cuts damage taken to 40% instead of the\n"
            "usual 60%. With Blocking learned, the same effect\n"
            "can occur outside Defend, by Skill difference.",
    483824: "This icon lights when the unit can transform. It\n"
            "can use the Transform command to change form and\n"
            "show different performance.",
    483984: "A unit with this icon lit can use the Combine\n"
            "command to merge several units into one powerful\n"
            "unit. The paired Separate command returns them to\n"
            "the original units.",
    484480: "Left is the unit's Move, same as the unit's Move\n"
            "stat. Right is move type, the ability to move in\n"
            "Air, Land and Water. White means passable; a dash\n"
            "means Air impossible, Land and Water difficult.",
    484704: "The unit's terrain rating, decided from pilot and\n"
            "unit ratings. Five ranks S, A, B, C, D from best,\n"
            "with A as standard (100%). Fighting on terrain you\n"
            "adapt well to improves hit, evade and defense.",
    484928: "How many squares the unit can move at once, and the\n"
            "terrain it moves well in. A squad's move is the\n"
            "average of its units. A lit Air means it can fly.",
    485120: "A gauge showing how many stages of Armor upgrade\n"
            "have been done. The gain per stage differs by unit.",
    485232: "A gauge showing how many stages of Mobility upgrade\n"
            "have been done.",
}
