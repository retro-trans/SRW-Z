# -*- coding: utf-8 -*-
"""Library / help database, batch 2: weapon stats, terrain bonuses, squad
bonuses and list-sorting help. Merged with library_en.LIBRARY_EN."""

LIBRARY_EN_B = {
    485344: "A gauge showing how many stages of Sight upgrade\n"
            "have been done. The gain per stage differs by unit.",
    485456: "The weapon's name. The icon at left is its class:\n"
            "<5> is a melee weapon, <6> is a ranged weapon.",
    485568: "The weapon type. Besides normal single-target\n"
            "weapons there are <9> for squad attacks, <10> to\n"
            "hit a whole squad, <8> for Tri Charge, <11> to hit\n"
            "all targets in range, and <22> for combined attacks.",
    485792: "The weapon's traits.\n"
            "<14>: adds a status effect on top of damage.\n"
            "<12>: usable after moving.\n"
            "<13>: a beam weapon, blockable by some barriers.",
    485984: "The weapon's attack power. The higher it is, the\n"
            "more damage it deals. Upgrading a weapon raises it.",
    486112: "The range the weapon can attack, shown as minimum\n"
            "to maximum range. Snipe or a high-performance radar\n"
            "can extend the maximum. Weapons with a range of\n"
            "only 1 cannot be extended.",
    486320: "How easily the weapon hits. It adjusts hit rate\n"
            "along with the unit's Sight and the pilot's Hit,\n"
            "so a higher value lands attacks more easily.",
    486464: "Short for critical rate bonus, how easily a critical\n"
            "hit occurs for 1.25x damage. The rate is set by the\n"
            "Skill gap with the enemy and the weapon's CRT.",
    486624: "How many times the weapon can fire, shown as current\n"
            "ammo over max ammo. Each use spends 1, and at 0 the\n"
            "weapon cannot be used. Resupply, a Cartridge or\n"
            "docking with a ship refills it.",
    486848: "The EN spent when the weapon is used, shown as cost\n"
            "EN (current EN). If current EN is below this value\n"
            "the weapon cannot be used. EN recovers via spirit\n"
            "commands, Resupply or terrain.",
    487072: "The Will needed to use the weapon, shown as required\n"
            "Will (current Will). If Will has not reached this\n"
            "value, the requirement is shown in red to mark it\n"
            "unusable.",
    487264: "The special skill and level needed to use the\n"
            "weapon. Unless the main pilot has learned that\n"
            "skill, the weapon cannot be used.",
    487424: "Ranked S to D like a unit's terrain rating, but it\n"
            "affects the damage dealt to a target on that\n"
            "terrain. So a unit with Sea S attacking underwater\n"
            "still does poor damage if the weapon is Sea C.",
    487680: "Effects that damage more than HP. They split broadly\n"
            "into two kinds.\n"
            "P-type: effects that act on the pilot.\n"
            "R-type: effects that act on the unit.",
    487888: "Besides status weapons, some weapons have these.\n"
            "Barrier Pierce: damage ignores barriers, with some\n"
            "exceptions. Ignore Size: ignores size-based damage\n"
            "reduction. Some skills nullify these effects.",
    488144: "A gauge showing how many stages of weapon upgrade\n"
            "have been done. Cost per stage differs by unit, and\n"
            "the attack gain differs by weapon.",
    488288: "Whether the weapon counts as melee or ranged. This\n"
            "decides which pilot stat is used to compute its\n"
            "attack power.",
    488416: "The weapon's full name, with model number.",
    488464: "Whether a MAP weapon can tell friend from foe.\n"
            "Valid hits only enemies in range; Invalid hits both\n"
            "allies and enemies in range.",
    488608: "The shape of a MAP weapon's area.\n"
            "Directional: a line in one of four directions.\n"
            "Targeted: an area centered on a point in range.\n"
            "Self-centered: an area centered on your unit.",
    488832: "The squad's Move over move type. Move is the average\n"
            "of each unit's Move, rounded down. Move type is\n"
            "white if all can move, grey if only some can\n"
            "(difficult), and blank if none can.",
    489072: "The bonus to defense gained from being on that\n"
            "terrain. Damage taken is reduced by that rate.\n"
            "No bonus applies while in the air.",
    489216: "The bonus to evasion gained from being on that\n"
            "terrain. It is subtracted from the enemy's final\n"
            "hit rate. No bonus applies while in the air.",
    489376: "HP recovered at the start of the ally phase while on\n"
            "that terrain. None recovers in the air.",
    489472: "EN recovered at the start of the ally phase while on\n"
            "that terrain. None recovers in the air.",
    489568: "The formation the squad currently has selected.\n"
            "Battleships and single-unit squads show none.",
    489680: "Support attack is possible. The icon number is\n"
            "how many times it can be used.",
    489760: "Support defend is possible. The icon number is\n"
            "how many times it can be used.",
    489840: "If even one unit in the squad has a repair device,\n"
            "resupply device, jamming or a lifter, the effect\n"
            "applies to the whole squad, not just that unit.\n"
            "This is called a squad bonus.",
    490048: "At the start of the ally phase, each unit in the\n"
            "squad recovers HP equal to 10% of max per repair\n"
            "unit. It works only if a unit in the squad has a\n"
            "repair device.",
    490224: "At the start of the ally phase, each unit in the\n"
            "squad recovers EN equal to 10% of max per resupply\n"
            "unit. It works only if a unit in the squad has a\n"
            "resupply device.",
    490400: "Adds +10 to final hit and evade rates. It works only\n"
            "if a unit in the squad has jamming.",
    490528: "Adds Air to the squad's move type, allowing flight.\n"
            "It works only if a unit in the squad has a lifter.",
    490656: "Sorts by battleship, event squad, then squad\n"
            "number. Units and squads that have finished\n"
            "acting are shown in dark text. Units with a status\n"
            "effect show <24>, and docked units show their ship.",
    490896: "Sorts by original unit order.",
    490928: "Sorts by the original pilot order.",
    490976: "Sorts by pilot level, highest first.",
    491024: "The effect of the search item.",
    491056: "The target the spirit command is used on.",
    491104: "Gives spirit orders to chosen pilots at once.\n"
            "<23> toggles each pilot between reserved (<25>) and\n"
            "not reserved (<26>); <27> confirms and uses every\n"
            "reserved spirit command.",
    491328: "Sorts by SP cost, ascending.",
}
