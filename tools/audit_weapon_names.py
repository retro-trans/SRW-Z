# -*- coding: utf-8 -*-
"""Audit every weapon/item name: does it FIT, and is it actually english?

Two failure modes, both seen on screen:

  ROMAJI   the original pass left katakana transliterated rather than
           translated - "High Sutoreitaretto" for ハイ・ストレイターレット.
           Detected by romanising the katakana ourselves and measuring how
           close the shipped english is to it; a real translation diverges,
           a transliteration does not.

  WIDTH    the name is drawn in a column sized for the japanese, and the
           Class column is drawn straight after it. The japanese string's
           width is the budget: full-width 21px, half-width 13px, the same
           model verify_ui_width.py uses.

Usage: audit_weapon_names.py [--romaji] [--over N] [--csv FILE]
"""
import io
import json
import os
import sys
import unicodedata

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(WORK, "analysis", "weapon_review.json")

# katakana -> romaji, enough to recognise a transliteration
K = {
    u"ア": "a", u"イ": "i", u"ウ": "u", u"エ": "e", u"オ": "o",
    u"カ": "ka", u"キ": "ki", u"ク": "ku", u"ケ": "ke", u"コ": "ko",
    u"サ": "sa", u"シ": "shi", u"ス": "su", u"セ": "se", u"ソ": "so",
    u"タ": "ta", u"チ": "chi", u"ツ": "tsu", u"テ": "te", u"ト": "to",
    u"ナ": "na", u"ニ": "ni", u"ヌ": "nu", u"ネ": "ne", u"ノ": "no",
    u"ハ": "ha", u"ヒ": "hi", u"フ": "fu", u"ヘ": "he", u"ホ": "ho",
    u"マ": "ma", u"ミ": "mi", u"ム": "mu", u"メ": "me", u"モ": "mo",
    u"ヤ": "ya", u"ユ": "yu", u"ヨ": "yo",
    u"ラ": "ra", u"リ": "ri", u"ル": "ru", u"レ": "re", u"ロ": "ro",
    u"ワ": "wa", u"ヲ": "o", u"ン": "n",
    u"ガ": "ga", u"ギ": "gi", u"グ": "gu", u"ゲ": "ge", u"ゴ": "go",
    u"ザ": "za", u"ジ": "ji", u"ズ": "zu", u"ゼ": "ze", u"ゾ": "zo",
    u"ダ": "da", u"ヂ": "ji", u"ヅ": "zu", u"デ": "de", u"ド": "do",
    u"バ": "ba", u"ビ": "bi", u"ブ": "bu", u"ベ": "be", u"ボ": "bo",
    u"パ": "pa", u"ピ": "pi", u"プ": "pu", u"ペ": "pe", u"ポ": "po",
    u"ヴ": "vu",
}
SMALL = {u"ャ": "ya", u"ュ": "yu", u"ョ": "yo", u"ァ": "a", u"ィ": "i",
         u"ゥ": "u", u"ェ": "e", u"ォ": "o"}


def romaji(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == u"ッ":                       # geminate: double the next
            nxt = s[i + 1] if i + 1 < len(s) else u""
            r = K.get(nxt, "")
            if r:
                out.append(r[0])
            i += 1
            continue
        if c == u"ー":                        # long vowel: drop it
            i += 1
            continue
        if i + 1 < len(s) and s[i + 1] in SMALL and c in K:
            base = K[c]
            out.append(base[:-1] + SMALL[s[i + 1]])
            i += 2
            continue
        out.append(K.get(c, ""))
        i += 1
    return "".join(out)


def norm(s):
    return "".join(ch for ch in s.lower() if ch.isalpha())


def ratio(a, b):
    """Longest-common-subsequence ratio, 0..1."""
    if not a or not b:
        return 0.0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(cur[j], prev[j + 1]))
        prev = cur
    return 2.0 * prev[-1] / (len(a) + len(b))


def px(s):
    return sum(21 if unicodedata.east_asian_width(c) in "WFA" else 13
               for c in s)


def load():
    return json.load(io.open(SRC, encoding="utf-8"))


def audit(rows):
    out = []
    for r in rows:
        jp, en = r["jp"], r["en"]
        kana = u"".join(c for c in jp if u"ァ" <= c <= u"ヴ" or c == u"ー")
        rj = romaji(kana)
        sim = ratio(norm(rj), norm(en)) if len(kana) >= 3 else 0.0
        out.append({
            "jp": jp, "en": en, "idx": r["idx"], "off": r["off"],
            "budget_px": px(jp), "en_px": px(en),
            "over": px(en) - px(jp), "romaji": rj, "sim": round(sim, 3),
        })
    return out


def main():
    rows = audit(load())
    over = int(sys.argv[sys.argv.index("--over") + 1]) if "--over" in sys.argv else 0

    if "--csv" in sys.argv:
        p = sys.argv[sys.argv.index("--csv") + 1]
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(u"idx\tjp\ten\tbudget_px\ten_px\tover\tromaji\tsim\n")
            for r in rows:
                fh.write(u"%d\t%s\t%s\t%d\t%d\t%d\t%s\t%s\n" % (
                    r["idx"], r["jp"], r["en"], r["budget_px"], r["en_px"],
                    r["over"], r["romaji"], r["sim"]))
        print("wrote %s" % p)

    wide = sorted([r for r in rows if r["over"] > over],
                  key=lambda r: -r["over"])
    print("=== OVER the japanese width (%d of %d) ===" % (len(wide), len(rows)))
    for r in wide[:40]:
        print("  %+5dpx  %-30s %-34s (%dpx vs %dpx)"
              % (r["over"], r["jp"], r["en"], r["en_px"], r["budget_px"]))

    if "--romaji" in sys.argv:
        rom = sorted([r for r in rows if r["sim"] >= 0.75],
                     key=lambda r: -r["sim"])
        print("\n=== looks like raw romaji, not english (%d) ===" % len(rom))
        for r in rom:
            print("  sim %.2f  %-28s %-30s (romaji: %s)"
                  % (r["sim"], r["jp"], r["en"], r["romaji"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
