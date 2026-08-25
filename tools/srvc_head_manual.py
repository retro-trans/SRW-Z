# -*- coding: utf-8 -*-
"""The 16 head-truncated quotes DeepSeek could not key.

All 16 contain the literal backslash-n break marker, which the model echoed back
in a different form, so the reply never matched the input key. Translated by hand
instead. Each is the TAIL of a longer line, so the English also begins
mid-thought - that matches what the game actually draws.

Merges into analysis/srvc_head_en.json.
"""
import io
import json
import os

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANUAL = {
    "4": "...!\\nBut!",
    "8": "You won't get past to this side!",
    "17": "\\nI'll crush you in one twist!",
    "23": "is a useless relic!!",
    "42": "Shiro!\\nAttack in time with me!",
    "43": "Fuhahahaha!\\nThat won't work on me!",
    "44": "Leben!\\nI am you!",
    "61": "If you stand in the way of our wish,\\nI won't show mercy!",
    "72": "\\nDon't look, it's embarrassing!",
    "74": "For their sake,\\nI'll fight too!",
    "78": "Take him down and\\nAEUG's command falls apart!",
    "88": "Why... why did it\\nturn out like this!!",
    "91": "How do I explain this\\nto Gramps...!",
    "92": "\\nThat's right!",
    "93": "-type SUMO!\\nLt. Harry!?",
    "107": "would stand in my way...!",
}

MAXCOL, MAXLINES = 48, 3


def main():
    p = os.path.join(WORK, "analysis", "srvc_head_en.json")
    en = json.load(io.open(p, encoding="utf-8"))
    added = bad = 0
    for k, v in MANUAL.items():
        segs = v.split("\\n")
        if len(segs) > MAXLINES or any(len(s) > MAXCOL for s in segs):
            print("  !! %s too wide: %r" % (k, v))
            bad += 1
            continue
        if any(ord(c) > 0x7F for c in v):
            print("  !! %s non-ascii" % k)
            bad += 1
            continue
        en[k] = v
        added += 1
    json.dump(en, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("added %d (rejected %d); srvc_head_en.json now %d entries"
          % (added, bad, len(en)))


if __name__ == "__main__":
    main()
