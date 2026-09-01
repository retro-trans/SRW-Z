# -*- coding: utf-8 -*-
"""Condensed DATA HELP entries for the 46 fields re-wrapping alone cannot fit.

The panel is 42 columns by 4 lines, so a field holds 168 columns. These 46 hold
143-199 columns of english after re-wrapping, and no amount of re-wrapping
makes text shorter - they had to be rewritten. Meaning is kept; what goes is
padding, restatement and detail the panel has no room for.

ENCODING. Bytes 0x2E-0x3D are control codes on this path - a raw ':' expands to
the protagonist's name, which is how "Setsuko" once appeared mid-sentence. So
'.' ':' ';' and digits are written FULLWIDTH here, exactly as the surrounding
japanese-derived text already does. '%' (0x25), '-' (0x2D), '?' (0x3F),
'(' ')' '<' '>' are outside the range and stay ASCII.

<NN> tokens are the game's own markup and are preserved verbatim - they expand
to icons and keyword names, and dropping one changes what the panel draws.

Usage: help_shorten.py <iso> [--apply]
"""
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "analysis", "compdata_raw.json")
NL = chr(10)
FP, FC, FS = chr(0xFF0E), chr(0xFF1A), chr(0xFF1B)   # ． ： ；
D = dict((str(i), chr(0xFF10 + i)) for i in range(10))


def fw(s):
    """digits -> fullwidth; '.' ':' ';' are already written fullwidth below."""
    return "".join(D.get(c, c) for c in s)


TEXT = {
 0x070958: "Short for Level, a guide to a pilot's strength{P} It rises with EXP, up to {99}{P} Higher levels improve stats and teach new skills and spirit commands{P}",
 0x070a10: "The pilot's morale{P} Higher Will means more damage and defense, and more usable weapons{P} It starts at {100} and ranges from {50} to {150}{P}",
 0x070b80: "Short for Spirit Points, shown as current over max{P} Spirit commands consume SP{P} Very few ways exist to recover it on a map, so spend it wisely{P}",
 0x070d58: "Total enemies shot down{P} Only the pilot who reduces an enemy's HP to {0} gets credit{P} At {50} kills a pilot becomes an Ace and gains a <1> icon{P}",
 0x070e10: "A bonus at {50} kills{P} Funds from downing enemies become {1}{P}{2}x and starting Will +{5}{P} Funds cap at {2}x, so even with Lucky it stops there{P}",
 0x070ed8: "The six pilot stats affecting combat - Melee, Ranged, Skill, Defense, Evade and Hit{P} They grow with level at a rate set by each pilot's growth type{P}",
 0x071050: "The pilot's piloting precision{P} Higher Skill raises the critical rate and helps skills judged by Skill gap, such as Re-Attack and Blocking, to fire{P}",
 0x071240: "The pilot's adaptation to each terrain, ranked S to D{P} In battle what applies is the unit's rating, from pilot and unit ratings together{P}",
 0x071378: "The skills a pilot has learned{P} A conditional skill changes color when it fires{P} Reaching set levels teaches new skills or raises their level{P}",
 0x071438: "Commands that aid battle{S} up to five are learned{P} Shown as Spirit (SP cost){P} Using one costs that SP{P} Effects and duration differ per command{P}",
 0x071600: "The unit's size class, from largest <15> down through <16> > <17> > <18> > <19>{P} The smaller side gains hit and evade, the larger a damage bonus{P}",
 0x0716b8: "The damage a unit can take{S} at {0} it is shot down{P} Shown as current over max HP{P} Lost HP is restored by repair units, spirit commands or parts{P}",
 0x071768: "The energy a unit carries, spent on weapons and movement{P} Shown as current over max EN{P} Lost EN is restored by resupply units, commands or parts{P}",
 0x0719b0: "The unit's adaptation to each terrain, ranked S to D{P} In battle what applies is the unit's rating, from pilot and unit ratings together{P}",
 0x071a68: "Move is how far a unit can travel{P} One square normally costs {1} Move, but some terrain costs more{P} That cost is called the movement cost{P}",
 0x071b20: "Move type is the terrain a unit can travel{P} If Air, Land or Water is listed it can change to that element{P} Air- or land-only warships cannot{P}",
 0x071d08: "Lights when the unit has a repair device{P} It can use Repair to restore HP{P} Its squad also recovers {10}% of max HP at the start of each ally phase{P}",
 0x071dc8: "Lights when the unit has a resupply device{P} Resupply fully restores EN and ammo for {10} Will{P} Its squad recovers {10}% of max EN each ally phase{P}",
 0x071ff0: "Lights when the unit carries a sword{P} With the Blocking skill, swords and solid-round weapons may be nullified by Cutting, by Skill difference{P}",
 0x0720b0: "Lights when the unit carries a shield{P} Defend cuts damage to {40}% instead of {60}%{P} With Blocking this can also occur outside Defend, by Skill{P}",
 0x0721f8: "Lights when the unit can use Combine to merge several units into one powerful unit{P} The paired Separate command returns them to the originals{P}",
 0x0723b0: "Left is Move, the unit's Move stat{P} Right is move type - Air, Land and Water{P} White means passable{S} a dash means Air impossible, the rest hard{P}",
 0x072478: "The unit's terrain rating, from pilot and unit ratings{P} Ranked S to D, with A as standard ({100}%){P} Good adaptation improves hit, evade and defense{P}",
 0x072768: "The weapon type{P} Besides normal single-target weapons{C} <9> squad attack, <10> hits a whole squad, <8> Tri Charge, <11> all in range, <22> combined{P}",
 0x072938: "The weapon's attack range, shown as minimum to maximum{P} Snipe or a high-performance radar can extend it{P} Range {1} weapons cannot be extended{P}",
 0x072b20: "How many times the weapon can fire, current over max{P} Each use spends {1}{S} at {0} it cannot be used{P} Resupply, a Cartridge or docking refills it{P}",
 0x072be0: "The EN spent when the weapon is used, shown as cost (current EN){P} Below that value it cannot be used{P} EN recovers via commands, Resupply or terrain{P}",
 0x072ca0: "The Will needed to use the weapon, shown as required (current){P} If Will has not reached it, the requirement is shown in red to mark it unusable{P}",
 0x072dd0: "Ranked S to D like a unit's rating, but it affects damage dealt on that terrain{P} A Sea S unit still does poor damage underwater with a Sea C weapon{P}",
 0x072f30: "Some weapons have these{P} Barrier Pierce{C} damage ignores barriers, with exceptions{P} Ignore Size{C} ignores size-based reduction{P} Some skills nullify them{P}",
 0x0731c0: "The shape of a MAP weapon's area{P} Directional{C} a line in one of four directions{P} Targeted{C} an area around a point in range{P} Self{C} around your unit{P}",
 0x073278: "The squad's Move over move type{P} Move is the average of each unit's, rounded down{P} Type is white if all can move, grey if some, blank if none{P}",
 0x073610: "If even one unit in the squad has a repair or resupply device, jamming or a lifter, the effect applies to the whole squad{P} This is a squad bonus{P}",
 0x0738f0: "Sorts by battleship, event squad, then squad number{P} Units that have acted show in dark text{P} A status effect shows <24>, docked units their ship{P}",
 0x073a78: "Gives spirit orders to chosen pilots at once{P} <23> toggles each between reserved (<25>) and not (<26>){S} <27> uses every reserved command{P}",
 0x074570: "The conditions for ending the battle map{P} Events or passing turns can change them or add new ones{P} The objective screen shows the latest{P}",
 0x074630: "The conditions that cause a game over{P} Events or passing turns can change them or add new ones{P} The objective screen shows the latest{P}",
 0x0746f0: "The conditions for an SR Point, which affects difficulty{P} Until they can be met they show as ???{P} Only {1} SR Point is earned per scenario{P}",
 0x074ad8: "Reserve squads with <23>, then <27> to apply all{P} The mark is <26> normally and <25> when reserved{P} If it matches the formation it becomes <29>{P}",
 0x0752d8: "The EXP earned in this battle{P} Downing an enemy gives the sum of the unit and pilot values{P} A hit gives one tenth, and non-leaders receive {75}%{P}",
 0x0755f0: "If a value rose with the level-up, the name shows in bright blue and the gain in green at the right{P} If several levels rose, totals are shown{P}",
 0x0758d8: "Shows how far the unit's stats have been upgraded{P} Taking HP, EN, Armor, Mobility and Sight to the top stage makes {100}% and unlocks a bonus{P}",
 0x075cd0: "Left is Move, right is move type{P} Move{C} how far the unit can travel{P} Move type{C} the terrain it can travel - air, land or underwater{P}",
 0x076848: "An MS with this icon carries a Satellite System{P} The number is the turns to finish charging{P} It shows Complete when ready, or NO MOON if it cannot{P}",
 0x076918: "Turns left until Gravion reaches graviton critical{P} At {0} the fusion is released and it cannot fuse again on this map{P} This can end the game{P}",
 0x077990: "The Move and move type of the squad at the cursor{P} Move is the average of each unit's, rounded down{P} White if all can move, grey if some{P}",
}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def expand(t):
    out = t.replace("{P}", FP).replace("{C}", FC).replace("{S}", FS)
    for n in ("150", "100", "99", "75", "60", "50", "40", "10",
              "5", "2", "1", "0"):
        out = out.replace("{%s}" % n, fw(n))
    return out


def wrap(text, width=42):
    words, out, line = text.split(), [], ""
    for w in words:
        cand = w if not line else line + " " + w
        if line and cols(cand) > width:
            out.append(line)
            line = w
        else:
            line = cand
    if line:
        out.append(line)
    return NL.join(out)


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(1823000 * 2048)
    d = bytes(banlz.decompress_record(f.read(400 * 2048), 0)[0])
    f.close()
    table = {}
    if os.path.exists(RAW):
        table = json.load(io.open(RAW, encoding="utf-8"))
    good = bad = 0
    for off in sorted(TEXT):
        z = d.find(b"\x00", off)
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        old = d[off:z].decode("cp932")
        new = wrap(expand(TEXT[off]))
        lines = new.split(NL)
        nb = new.encode("cp932")
        why = None
        if len(lines) > 4:
            why = "%d lines" % len(lines)
        elif max(cols(l) for l in lines) > 42:
            why = "%d cols" % max(cols(l) for l in lines)
        elif len(nb) >= k - off:
            why = "%d bytes, slot %d" % (len(nb) + 1, k - off)
        # <NN> markup carries its own ASCII digits, which ARE in the control
        # range but are the game's own tokens - they appear in the japanese
        # too and the renderer consumes them. Strip the tokens before checking
        # for a raw control byte that would actually reach the font path.
        elif any(0x2E <= c <= 0x3D
                 for c in re.sub(r"<-?\d+>", "", new).encode("cp932")):
            why = "raw control byte 0x2E-0x3D outside a <NN> token"
        if why:
            bad += 1
            print("REFUSED %#08x  %s" % (off, why))
            for l in lines:
                print("    %2d| %s" % (cols(l), l))
        else:
            good += 1
            table["0x%06x" % off] = [old, new]
    io.open(RAW, "w", encoding="utf-8", newline=NL).write(
        json.dumps(table, ensure_ascii=False, indent=1))
    print("accepted %d, refused %d -> %s" % (good, bad, os.path.basename(RAW)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
