# -*- coding: utf-8 -*-
"""Replace Japanese names left inside otherwise-English dialogue lines.

219 T entries are English prose with the character's name still in Japanese -
usually the speaker: 'ジ・エーデル\\n"World domination..?"'. They pass every
existing check because those validate byte budgets, never language.

Names come from analysis/glossary.json plus EXTRA below for the 16 it lacks.
Longest-first substitution, so ジ・エーデル is consumed before エーデル.

Writes analysis/namefix_en.json, merged into the override map by apply_stage.
Kept SEPARATE from tighten_en.json because gen_tighten.py regenerates that file
and would otherwise wipe these.
"""
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import apply_stage as A

# Not in glossary.json. ジ・エーデル is the antagonist's name (66 lines, always as
# the speaker), NOT a variant of エーデル - substitute it first.
EXTRA = {
    u"ジ・エーデル": "The Edel",
    u"ツィーネ": "Tsine",
    u"エーデル": "Edel",
    u"斗牙": "Touga",
    u"ガットラー": "Gattler",
    u"レーベン": "Leben",
    u"ジーラ": "Zila",
    u"ガガーン": "Gagan",
    u"ジェミー": "Jamie",
    u"ヒューギ": "Hugi",
    u"ギジェット": "Gidget",
    u"桂": "Kei",
    u"テラル": "Teral",
    u"ネグロス": "Negros",
    u"ダルトン": "Dalton",
}

# NOT a name: 空 here is the tail of 時空崩壊 (spacetime collapse) - the translator
# dropped half the compound and left the kanji in the English line.
PHRASE = {
    u"the空 collapse": "the spacetime collapse",
}

# Rows where substituting the name pushes the line past its slot.
MANUAL = {
    # 'Gengoro\n"What's wrong, Kappei?!"' is 32 in a 31-byte slot
    "132:386": "Gengoro\n\"What is it, Kappei?!\"",
}

JP = re.compile(r"[぀-ヿ一-鿿]+")


def main():
    gloss = json.load(io.open(os.path.join(WORK, "analysis", "glossary.json"),
                              encoding="utf-8"))
    names = dict(gloss)
    names.update(EXTRA)
    # longest first so compound names win
    ordered = sorted(names.items(), key=lambda kv: -len(kv[0]))

    items = json.load(io.open(os.path.join(WORK, "analysis", "passthrough_jp.json"),
                              encoding="utf-8"))
    part = [x for x in items if not x["identical"]]

    out, residue = {}, []
    cache = {}
    for x in part:
        n = x["rec"]
        if n not in cache:
            p = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
            cache[n] = bytearray(open(p, "rb").read())
        orig = cache[n]
        key = "%d:%d" % (n, x["row"])
        en = MANUAL.get(key, x["en"])
        for a, b in PHRASE.items():
            en = en.replace(a, b)
        for jp, eng in ordered:
            if jp in en:
                en = en.replace(jp, eng)
        leftover = JP.findall(en)
        if leftover:
            residue.append((x, leftover, en))
            continue
        # must still fit
        off, bud = x["offset"], x["budget"]
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        is_dlg = ("\n" in en and len(first) <= 15
                  and not first.endswith((".", "!", "?")))
        enc = bytes(orig[off:off + lead]) + A.pencode(en, "ascii" if is_dlg else "menu")
        if len(enc) > bud:
            residue.append((x, ["OVER BUDGET %d>%d" % (len(enc), bud)], en))
            continue
        out["%d:%d" % (n, x["row"])] = en

    p = os.path.join(WORK, "analysis", "namefix_en.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("partial-Japanese rows : %d" % len(part))
    print("fixed                 : %d" % len(out))
    print("residue               : %d" % len(residue))
    for x, left, en in residue[:15]:
        print("   rec%03d row %-5d %s" % (x["rec"], x["row"], left))
        print("      %r" % en[:70])
    print("\nwritten -> %s" % p)


if __name__ == "__main__":
    main()
