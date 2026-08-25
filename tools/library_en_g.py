# -*- coding: utf-8 -*-
"""Library / help database, batch 7: map command descriptions, leader-bonus
condition labels, formation summaries, full-upgrade bonuses and the
Intermission command help."""

LIBRARY_EN_G = {
    513584: "Move to another spot within range. After moving,\n"
            "some individual commands can still be used.",
    513680: "Attack an enemy. Before moving all weapons can be\n"
            "used; after moving only P-type weapons.",
    513776: "Move into the air. 10 EN is spent at\n"
            "the start of each ally phase.",
    513856: "Move to the ground. You gain terrain bonuses to\n"
            "defense and evasion.",
    513936: "Move underwater. Underwater, damage from beam\n"
            "weapons is greatly reduced.",
    514016: "Persuade an adjacent enemy. The result can change\n"
            "how the story unfolds.",
    514096: "Re-launch a squad docked in a ship.\n"
            "Usable after the ship has acted.",
    514176: "Dock in a ship. While docked, HP and EN\n"
            "recover 15% and ammo fully each ally phase.",
    514272: "Take an adjacent squad aboard. Usable after\n"
            "moving, but doing so ends your action.",
    514368: "Restore HP to an adjacent ally squad or your own.\n"
            "The amount rises with the pilot's level.",
    514464: "Fully restore EN and ammo for one unit in an\n"
            "adjacent ally squad or your own.",
    514544: "Transform into another form. Stats\n"
            "and move type change.",
    514624: "Change the Impulse Gundam's Silhouette. Usable\n"
            "while the Minerva has sortied.",
    514720: "Split one unit into several. The resulting units\n"
            "appear in the same squad.",
    514816: "Merge several units into one. HP and EN become\n"
            "the averaged ratio of the parts.",
    514912: "Fuse with Grandiva to strengthen the unit. The\n"
            "fusion is released after 3 turns.",
    515008: "Use an equipped part. Battleships can also use\n"
            "them on adjacent ally units.",
    515104: "Change the formation. The leader and order can be\n"
            "changed at the same time.",
    515184: "Use a spirit command. Lasting effects are shown\n"
            "on the squad status screen.",
    515280: "Show squad status. From there you can\n"
            "go on to unit status.",
    515360: "End the action without doing anything after\n"
            "moving. Check once more for anything left to do.",
    515456: "Restore God Sigma's EN to maximum. Usable only\n"
            "once per battle map.",
    515552: "End the ally phase and move to the enemy phase.",
    515616: "Search robot and pilot data such as\n"
            "spirits and special abilities.",
    515696: "Show a list of deployed units. You can switch\n"
            "between squad view and unit view.",
    515792: "Show victory, defeat and SR Point\n"
            "conditions for this map.",
    515872: "Show the current situation and cumulative data.",
    515936: "Change the formation of all squads that have not\n"
            "acted.",
    516000: "Set quick commands, choose BGM and other system\n"
            "settings.",
    516080: "Save the state of this battle map so you can\n"
            "resume from the same point.",
    516160: "Choose the squads to send out. How many can\n"
            "sortie differs by battle map.",
    516240: "Form squads for battle. Same as the\n"
            "Intermission command.",
    516320: "Check the map terrain and change squad sortie\n"
            "positions.",
    516384: "Finish preparations and send out the force.",
    516432: "Check the map terrain.",
    516464: "----",
    516480: "Always",
    516496: "Adjacent squads",
    516512: "Except MAP and range 1, +1",
    516544: "Squad Move +1",
    516576: "Adjacent squad EN cost",
    516600: "Enemy phase",
    516624: "Squad attack",
    516640: "Ally phase",
    516656: "Melee weapons",
    516672: "Ranged weapons",
    516688: "Support attack",
    516704: "vs male +20%, vs female -",
    516736: "Adj. squad, vs Gaizok",
    516760: "vs Zeravire",
    516776: "vs Datenshi",
    516792: "vs air units",
    516816: "Support defend",
    516832: "Adjacent squad",
    516848: "Air terrain to S",
    516880: "Land terrain to S",
    516912: "Sea terrain to S",
    516944: "All terrain to A or better",
    517008: "Cutting, Shield Defend",
    517032: "P-type weapons",
    517048: "All status weapons",
    517072: "Grants [Morale Up]",
    517104: "Grants [Will+ (Evade)]",
    517136: "Grants [Will+ (Damage)]",
    517168: "Grants [Will+ (Hit)]",
    517264: "Tri Charge usable, squad attack not.\n"
            "Support defend usable. Members gain\n"
            "defense and evade vs all-out.",
    517376: "Squad attack focuses one enemy,\n"
            "members at 50% power. Support defend\n"
            "usable. Barrier covers all units.\n"
            "Leader gains defense vs all-out.",
    517520: "Squad attack hits separate enemies,\n"
            "members at 80% power. No support\n"
            "defend. Members gain defense.",
    517688: "Mobility +10%",
    517704: "Sight +10%",
    517720: "Armor +10%",
    517736: "Move +1",
    517760: "Grants Jamming",
    517792: "All Air terrain, unit and weapons, to S",
    517840: "All Land terrain, unit and weapons, to S",
    517888: "All Sea terrain, unit and weapons, to S",
    517936: "All Space terrain, unit and weapons, to S",
    517984: "Barrier and armor cost 0 EN to activate",
    518032: "Range +1 except MAP and range 1 weapons",
    518080: "All weapons critical bonus +10%",
    518176: "~[Full Upgrade Bonus (Range)]~",
    518240: "：Menu",
    518272: "：End setup",
    518304: "：Map",
    518336: "：Mark",
    518376: "：Default",
    518392: "：All Random",
    518448: "：---",
    518464: "：----",
    518480: "A part once swapped cannot be swapped again on\n"
            "the same map. Swap it?",
    518560: "Three turns after fusing, God Gravion reaches\n"
            "graviton critical and the fusion is released.\n"
            "After that it cannot fuse again on the same map.\n"
            "Fuse?",
    518720: "Show stats from the unit list.",
    518752: "Upgrade unit performance and weapon power.",
    518800: "Equip the unit with its own swap parts.",
    518848: "Equip the unit with parts.",
    518896: "Check what parts are equipped.",
    518928: "Search spirits, skills and abilities.",
    518976: "Show stats from the pilot list.",
    519024: "Train pilot stats and learn skills.",
    519072: "Move a different pilot into the unit.",
    519120: "End the Intermission.",
    519168: "Change the squad line-up.",
    519200: "Buy and sell parts and units.",
    519248: "Change various settings.",
    519280: "Save and load.",
    519312: "Unit-related operations.",
    519344: "Pilot-related operations.",
    519376: "Upgrades are not available in EX Hard mode.",
    519424: "Training is not available in EX Hard mode.",
    519472: "Basic Order",
    519504: "Balance Order",
    519528: "Keyword",
}
