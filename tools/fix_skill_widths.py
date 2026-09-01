# -*- coding: utf-8 -*-
"""Shorten the skill names that overflow their column in the Search grid.

The skill picker is a FOUR-COLUMN grid with fixed x positions, so each cell has
a hard pixel budget and the font is fixed half-width - VWF is still Milestone 4
in docs/VWF.md, "TODO", and its own honest assessment calls it a multi-session
build. Shortening is the fix available today.

THE BUDGET, measured off the screen rather than guessed: "Assist Atk" (10
characters) sits clear of the next column and "Support Atk" (11) runs into
"Chain Atk". So ten characters is the limit, and 13 of the 29 names were over
it - "Morale+ (Damage)" by six.

WHILE FIXING THE WIDTH, A NAMING BUG. Four skills are the same japanese family,
気力＋（回避/命中/ダメージ/撃破), and three shipped as "Will+ (…)" while the
fourth shipped as "Morale+ (Damage)". They are now one family again.

Every replacement is SHORTER than what it replaces, so each is written in place
and NUL-padded; nothing moves and no pointer changes.

Usage: fix_skill_widths.py <iso> [--write]
"""
import re
import sys

LBA, VBASE, FOFF, ELF_SIZE = 455, 0x100000, 0x1A80, 3471624

# old -> new. The game already abbreviates Atk / Def / Tech / SP in this list,
# so these are in keeping rather than a new convention.
FIX = [
    ("Support Atk",      "Sup Atk"),
    ("Support Def",      "Sup Def"),
    ("Rising Will",      "Morale Up"),
    ("Will+ (Evade)",    "Will+Evade"),
    ("Will+ (Hit)",      "Will+Hit"),
    ("Morale+ (Damage)", "Will+Dmg"),      # was the odd one out
    ("Will+ (Kill)",     "Will+Kill"),
    ("Will Cap Up",      "Will Cap+"),
    ("Ignore Size",      "Ignore Sz"),
    ("Spirit Resist",    "Mind Guard"),
    ("Repair Skill",     "Repair"),
    ("Supply Skill",     "Supply"),
    ("Cyber-Newtype",    "Cyber-NT"),
    ("Newtype (X)",      "Newtype X"),
    # The tabs across the top of the same screen. These are sized to the
    # japanese - 小隊ボーナス is 126px and "Squad Bonus" is 143px - so the
    # english overflows at EVERY site, not just this screen, which is why
    # shortening every instance is safe rather than over-reach.
    ("Squad Bonus",      "Sq Bonus"),
]


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * 2048)
    e = bytearray(f.read(ELF_SIZE))
    done = skipped = 0
    for old, new in FIX:
        ob, nb = old.encode("cp932"), new.encode("cp932")
        if len(nb) > len(ob):
            print("REFUSED %r -> %r is longer" % (old, new))
            skipped += 1
            continue
        hits = []
        i = 0
        while True:
            i = bytes(e).find(ob, i)
            if i < 0:
                break
            z = bytes(e).find(b"\x00", i)
            if z - i == len(ob):        # a whole field, not a substring
                hits.append(i)
            i += 1
        if not hits:
            print("NOT FOUND %r" % old)
            skipped += 1
            continue
        for h in hits:
            e[h:h + len(ob)] = nb + b"\x00" * (len(ob) - len(nb))
        done += len(hits)
        print("   %-18r -> %-12r %2d -> %2d ch, %d place(s)"
              % (old, new, len(old), len(new), len(hits)))
    print("%d field(s) shortened, %d skipped" % (done, skipped))
    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return 0
    f.seek(LBA * 2048)
    f.write(bytes(e))
    f.close()
    print("ELF rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
