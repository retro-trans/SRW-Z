# -*- coding: utf-8 -*-
"""Name corrections from issue #2 (creepgnome), applied to COMPDATA in 0.9.3.

Two kinds of fix live here.

WEAPON AND UNIT NAMES left as romaji by the original translation pass. Every
one was matched as a WHOLE NUL-terminated field, never as a substring - a bare
substring replace on a string pool hits real prose and other names.

PILOT NAME ORDER. A pilot record is three fields:

    [A 21B] short name    甲児 Koji
    [B 23B] surname       兜   Kabuto
    [C 24B] given name    甲児 Koji

and the game DISPLAYS B followed by C with no separator, which is why the
Mazinger pilot showed as "KabutoKouji". Western order is produced by putting
the given name in B (with a trailing space) and the surname in C, so B+C reads
"Koji Kabuto".

This is NOT safe to apply across every pilot. The three-field shape is not
uniform - オリバー/オリバー/ジャック does not follow the 甲児/兜/甲児 pattern - so a
blanket swap would scramble names rather than reorder them. Records are keyed
here by their JAPANESE surname and handled one family at a time.
"""

# whole-field replacements in the COMPDATA string pool
WEAPONS = {
    "Bageena": "Bajeena",
    "Lady Commando": "Lady Command",
    "Heat Hoku": "Heat Hawk",
    "Borujanon Machine Gun": "Borjarnon Machine Gun",
    "Borujanon Machine Gun (Rapid)": "Borjarnon Machine Gun (Rapid)",
    "Borujanon Bazooka": "Borjarnon Bazooka",
    "Plasma Gimikku": "Plasma Gimmick",
    "Neburu Missile": "Navel Missile",
    "Borotto Punch": "Borot Punch",
    "Borotto Special": "Borot Special",
    "Borottodainamikku Special": "Borot Dynamic Special",
    "Long Renji Laser Cannon (Rapid)": "Long Range Laser Cannon (Rapid)",
    "Long Renji Saber": "Long Range Saber",
    "Raiga Missile": "Liger Missile",
    "Raiga Missile (Rapid)": "Liger Missile (Rapid)",
    "Mashin Cannon": "Machine Cannon",
    "Nozu Beam Cannon": "Nose Beam Cannon",
    "Risuto Beam Cannon": "Wrist Beam Cannon",
    "Daitarn Sunappa": "Daitarn Snapper",
    "Beam Doraibu Unit": "Beam Drive Unit",
    "Boomerang Idiomu": "Boomerang Idiom",
    "Walker Galliar": "Walker Gallia",
    "Full Epon Combination": "Full Weapon Combination",
    "Za Glory Star": "The Glory Star",
    # ダイザーフルパワー. Both of these were the same attack under two wrong
    # names. "Dizer Full Power" is 16 bytes and the slot holds 15, and the
    # surrounding list already abbreviates ("Transfm"), so it is shortened.
    "Daizafuru Power": "Dizer Full Pwr",
    "Duke Full Power": "Dizer Full Pwr",
    # the japanese stores this with fullwidth digits: ２０ ０mm
    "２０ ０mm Rocket Ashisuto Gun": "200mm Rocket Assist Gun",
}

# japanese surname -> english surname, for records reordered to western form.
# The B field becomes "<given> " and the C field becomes the surname.
SURNAMES = {
    "兜": "Kabuto",      # 兜 - Koji, Shiro, Kenzo
}

# given names whose romanisation was also wrong
GIVEN = {
    "Kouji": "Koji",
}
