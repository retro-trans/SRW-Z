# -*- coding: utf-8 -*-
"""Hand translations for the battle lines the model would not return.

These 24 are not hard and they are not too long - median 15 Japanese characters
in a box that takes 2 rows. DeepSeek simply kept dropping them from its JSON
across eleven rounds, converging with nothing added, so they are written by hand
instead of burning more rounds on them.

Keyed by the Japanese exactly as it appears in srvc_work.json (wrapper 「」
stripped, breaks normalised to a literal backslash-n). Validated against
srvc_refit's per-line budget - min(37, 2 x longest Japanese segment), 2 rows -
NOT the flat 48 the first pass used, which is what let the text overflow the box
in v1.31. 15 of these 24 had to be shortened once that rule was applied.

Usage: srvc_manual.py [--write]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from srvc_refit import budgets, fits

WORK = r"E:\Projects\SRW Z\_work"

MANUAL = {
    u"\u4e00\u4e07\u4e8c\u5343\u5e74\u306e\u95c7\u306e\u4f7f\u5f92\u3081\u2026":
        "Dark apostle of twelve\\nthousand years...",
    u"\u30ac\u30f3\u30c0\u30e0\u306e\u3053\u3068\u306f\u3088\u304f\u77e5\u3063"
    u"\u3066\u3044\u308b\u3093\u3067\u306a\uff01":
        "I know all about the Gundam!",
    u"\u3046\u3050\u3063\uff01\u3000\u53cd\u4e71\u5206\u5b50\u5171\u3081\uff01":
        "Ugh! Damn rebels!",
    u"\u304d\u3001\u8cb4\u69d8\u3089\u306b\u5927\u7fa9\u306f\u306a\u3044\uff01":
        "Y-You have no justice!",
    u"\u306f\u3001\u306f\u3044\u2026\\n\u30a2\u30dd\u30ed\u541b\u306e\u304a"
    u"\u304b\u3052\u3067\u52a9\u304b\u308a\u307e\u3057\u305f\u2026\uff01":
        "Y-Yes...\\nThanks to Apollo, I made it...!",
    u"\u307f\u3001\u898b\u5931\u3063\u305f\u304b\uff01":
        "Did I lose him!?",
    u"\u304f\u3063\uff01\u3000\u5974\u306f\u3069\u3053\u3078\u884c\u3063"
    u"\u305f\uff01\uff1f":
        "Tch! Where did he go!?",
    u"\u65e9\u304f\u5974\u3092\u898b\u3064\u3051\u51fa\u3055\u306a\u3051"
    u"\u308c\u3070\u2026\uff01":
        "I have to find him, fast...!",
    u"\u3053\u306e\u307e\u307e\u62bc\u3057\u5207\u3089\u308c\u3066\u306a\u308b"
    u"\u3082\u306e\u304b\uff01":
        "I won't let them overpower me!",
    u"\u3046\u304a\u3063\uff01\uff1f\u3000\u8106\u3044\u6240\u306b\uff01\uff01":
        "Whoa!? A weak spot!!",
    u"\u3059\u3001\u65e2\u306b\u899a\u609f\u306f\u51fa\u6765\u3066\u3044"
    u"\u308b\uff01":
        "I-I'm already prepared!",
    u"\u80cc\u4e2d\u306f\u304a\u524d\u306b\u4efb\u305b\u3066\u308b\u304b"
    u"\u3089\u306a\uff01":
        "You've got my back!",
    u"\u30d5\u30f3\u2026\u8abf\u5b50\u306e\u3044\u3044\u5974\u3060":
        "Hmph... smooth one",
    u"\u307e\u3042\u307e\u3042\u3001\u76f8\u5909\u308f\u3089\u305a\u3068"
    u"\u3044\u3046\u3053\u3068\u3067":
        "Well now, same as always",
    u"\u8ff7\u3044\u306f\u81ea\u5206\u3092\u6bba\u3059\u3053\u3068\u306b"
    u"\u306a\u308b\uff01":
        "Hesitation will kill you!",
    u"\u4e0b\u304c\u308c\u3001\u30a2\u30dd\u30ea\u30fc\uff01":
        "Fall back, Apolly!",
    u"\u6ce2\u72b6\u653b\u6483\u3092\u4ed5\u639b\u3051\u308b\uff01":
        "Wave attack!",
    u"\u3053\u3053\u306f\u69d8\u5b50\u3092\u898b\u308b\u3057\u304b\u306a"
    u"\u3044\u304b\u2026\uff01":
        "Nothing to do but watch...!",
    u"\u3053\u3046\u306a\u3063\u305f\u3089\u3001\u5974\u3092\u9053\u9023"
    u"\u308c\u306b\u3057\u3066\u3067\u3082\u2026\uff01":
        "Then I'll take him down with me...!",
    u"\u304a\u4e92\u3044\u96e3\u5100\u306a\u4eba\u751f\u3092\u80cc\u8ca0"
    u"\u3063\u3061\u307e\u3063\u305f\u306a\u2026\\n\u30db\u30e9\u30f3\u30c9"
    u"\uff01\uff01":
        "We both got rough lives...\\nHolland!!",
    u"\u3084\u306f\u308a\u7981\u5fcc\u3067\u3042\u308b\u3079\u304d\u7269"
    u"\u3092\u4f7f\u3063\u305f\u8005\u306f\\n\u7f70\u305b\u3089\u308c\u308b"
    u"\u3068\u3044\u3046\u306e\u304b\u2026\uff01\uff1f":
        "So those who use the forbidden\\nreally are punished...!?",
    u"\u3042\u3089\u3041\uff1f\\n\u3082\u3057\u304b\u3057\u3066\u3001\u3042"
    u"\u305f\u3057\u306e\u30df\u30b9\uff1f":
        "Oh my?\\nWas that my mistake?",
    u"\u305d\u308c\u304c\u30db\u30e9\u30f3\u30c9\u9054\u3068\u306e\u7d04"
    u"\u675f\u3060\u304b\u3089\u306a\uff01":
        "That's my promise to Holland!",
    u"\u3063\u305f\u304f\u3088\uff01\\n\u8ecd\u304c\u6226\u3046\u76f8\u624b"
    u"\u306f\u5225\u306b\u3044\u308b\u3093\u3058\u3083\u306d\u3048\u304b"
    u"\uff01\uff1f":
        "Damn it!\\nThe army's fighting the wrong foe!?",
}


def main():
    write = "--write" in sys.argv
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))
    p = os.path.join(WORK, "analysis", "srvc_en.json")
    en = json.load(io.open(p, encoding="utf-8"))
    by_jp = {x["jp"]: x for x in items}

    added = unmatched = rejected = 0
    for jp, v in MANUAL.items():
        x = by_jp.get(jp)
        if not x:
            print("  NO MATCH in worklist: %r" % jp[:34])
            unmatched += 1
            continue
        cols, rows = budgets(jp)
        w = fits(v, cols, rows)
        if w:
            print("  REJECTED (%s): %s" % (w, v))
            rejected += 1
            continue
        if str(x["i"]) in en:
            continue
        en[str(x["i"])] = v
        added += 1
        print("  x%-3d %-34s -> %s" % (x["n"], jp.replace("\\n", " / ")[:32],
                                       v.replace("\\n", " / ")))

    print("\nadded %d, unmatched %d, rejected %d" % (added, unmatched, rejected))
    left = [x for x in items if str(x["i"]) not in en]
    print("remaining Japanese: %d lines, %d slots"
          % (len(left), sum(x["n"] for x in left)))
    if write and added:
        json.dump(en, io.open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("wrote %s (%s entries)" % (p, "{:,}".format(len(en))))
    elif added:
        print("(report only; pass --write to apply)")


if __name__ == "__main__":
    main()
