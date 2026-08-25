# -*- coding: utf-8 -*-
"""The last 19 battle voice lines, translated by hand.

srvc_deepseek rejected these for exceeding the display limit (48 half-width
columns x 3 lines), not for meaning - they are ordinary complete quotes. Break
them explicitly instead.

The line-break marker in SRVC is a LITERAL backslash-n (two characters), not
0x0A. 双翅/戦翅 follow the established 翅 sibling romanisation already used for
Zushi / Shishi / Ryoshi / Onshi / Goushi.

Merges into analysis/srvc_en.json, keyed by worklist index.
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINES = {
    "4508": "How far can I go against Shinn\\nand that new model...!?",
    "529": "I won't forgive anyone who wrecks\\nthe princess's heaven!",
    "774": "I won't forgive anyone who makes\\nthe princess sad!!",
    "7536": "Why can't you understand\\nthe Chairman's thinking!?",
    "7826": "Protecting the operations chief is my job too.",
    "2496": "Understood! All hands,\\nprepare for ship-to-ship combat!",
    "17363": "If I can die with the ship I loved,\\nI have no regrets...",
    "18063": "This is what happens when you\\nchallenge without power!",
    "9057": "If I aim for the opening\\nfrom the first attack...!",
    "1865": "I can see it... the darkness\\nof twelve thousand years...",
    "22580": "This is what you get for closing in carelessly!",
    "23610": "Soshi, fighting like that...",
    "847": "Apostle of the twelve-thousand-year darkness...",
    "25558": "I won't let the flame of this\\nvaliant battle festival die!",
    "25572": "Soshi... a child after all, powerless...",
    "25587": "Very well... time to show you a Senshi's battle.",
    "2932": "...Heh, Reika's recklessness...\\nI look forward to it...",
    "25688": "Th-this is the gap between\\nhuman and Fallen Angel...!?",
    "25695": "Continuous fire on the enemy ahead!\\nDon't let them escape!",
}

MAXCOL, MAXLINES = 48, 3


def main():
    p = os.path.join(WORK, "analysis", "srvc_en.json")
    en = json.load(io.open(p, encoding="utf-8"))
    work = {str(w["i"]): w for w in
            json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))}

    added = bad = 0
    for k, v in LINES.items():
        if k not in work:
            print("  !! index %s not in worklist" % k)
            continue
        segs = v.split("\\n")
        if len(segs) > MAXLINES or any(len(s) > MAXCOL for s in segs):
            print("  !! %s exceeds %dx%d: %r" % (k, MAXCOL, MAXLINES, v))
            bad += 1
            continue
        if any(ord(c) > 0x7F for c in v):
            print("  !! %s has non-ascii" % k)
            bad += 1
            continue
        en[k] = v
        added += 1

    json.dump(en, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("added %d (rejected %d) -> %s now has %d entries"
          % (added, bad, p, len(en)))


if __name__ == "__main__":
    main()
