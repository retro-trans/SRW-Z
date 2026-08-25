# -*- coding: utf-8 -*-
"""Translate the remaining unit (mecha) display names in COMPDATA.

Weapon names are 100% done; unit names are not. 773 of ~1,184 name slots in
0x6D0C0..0x71C30 are still Japanese - patch_compdata's UNITS pass only ever had
~207 entries from the akurasu list. The rest are mostly katakana mecha names,
which transliterate mechanically.

Reuses the weapon pipeline's parts:
  - analysis/akurasu_units.txt  : canon English names scraped from the wiki
  - kata_romaji.py              : Hepburn fallback for anything not in canon
  - NEC roman numerals Ⅰ/Ⅱ/Ⅲ map to I/II/III (ビアルⅠ世 -> Bial I, オーガスⅡ ->
    Orguss II); these are the same characters that broke the dialogue extractor.

Writes analysis/units_en.json {japanese: english}, budget-checked against the
real NUL slots (budget = slot - 1, the terminator must survive).
"""
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz
import kata_romaji

ROMAN = {u"Ⅰ": "I", u"Ⅱ": "II", u"Ⅲ": "III", u"Ⅳ": "IV", u"Ⅴ": "V",
         u"Ⅵ": "VI", u"Ⅶ": "VII", u"Ⅷ": "VIII", u"Ⅸ": "IX", u"Ⅹ": "X"}
FW = {u"０": "0", u"１": "1", u"２": "2", u"３": "3", u"４": "4", u"５": "5",
      u"６": "6", u"７": "7", u"８": "8", u"９": "9", u"Ａ": "A", u"Ｂ": "B",
      u"Ｃ": "C", u"Ｄ": "D", u"Ｅ": "E", u"Ｆ": "F", u"Ｇ": "G", u"Ｈ": "H",
      u"Ｉ": "I", u"Ｊ": "J", u"Ｋ": "K", u"Ｌ": "L", u"Ｍ": "M", u"Ｎ": "N",
      u"Ｏ": "O", u"Ｐ": "P", u"Ｑ": "Q", u"Ｒ": "R", u"Ｓ": "S", u"Ｔ": "T",
      u"Ｕ": "U", u"Ｖ": "V", u"Ｗ": "W", u"Ｘ": "X", u"Ｙ": "Y", u"Ｚ": "Z",
      u"　": " ", u"・": " ", u"－": "-", u"＝": "=", u"＋": "+"}

# 世 after a roman numeral is a regnal number: ビアルⅠ世 = "Bial I", not "Bial I Sei"
SUFFIX_SEI = re.compile(u"([ⅠⅡⅢⅣⅤ])世")


def norm(s):
    """Fold fullwidth to halfwidth for MATCHING only.

    The wiki list writes 'マジンガーZ' with a halfwidth Z; COMPDATA stores
    'マジンガーＺ' with a fullwidth one. Without folding, nothing matches at all
    (the first run found 0 of 249).
    """
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:          # fullwidth ASCII block
            out.append(chr(o - 0xFEE0))
        elif ch in ROMAN:
            out.append(ROMAN[ch])
        elif ch in (u"　", u"・"):
            out.append(" ")
        else:
            out.append(ch)
    return re.sub(r"\s+", "", "".join(out)).lower()


def load_canon():
    """{normalised japanese: english} from the akurasu list ('jp|en' per line)."""
    p = os.path.join(WORK, "analysis", "akurasu_units.txt")
    out = {}
    if not os.path.exists(p):
        return out
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if "|" not in line:
            continue
        a, b = line.split("|", 1)
        a, b = a.strip(), b.strip()
        if a and b:
            out[norm(a)] = b
    return out


def translit(jp):
    s = SUFFIX_SEI.sub(lambda m: ROMAN[m.group(1)], jp)
    for k, v in ROMAN.items():
        s = s.replace(k, v)
    for k, v in FW.items():
        s = s.replace(k, v)
    # katakana runs -> Hepburn, everything else left for review
    out = []
    buf = []
    for ch in s:
        if u"ァ" <= ch <= u"ヿ" or ch == u"ー":
            buf.append(ch)
        else:
            if buf:
                out.append(kata_romaji.romanize("".join(buf)))
                buf = []
            out.append(ch)
    if buf:
        out.append(kata_romaji.romanize("".join(buf)))
    s = "".join(out)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main():
    items = json.load(io.open(os.path.join(WORK, "analysis", "abilities_jp.json"),
                              encoding="utf-8"))
    # descriptions end in 。 and are prose, not names - keep them out
    names = [x for x in items
             if len(x["jp"]) < 20 and "\n" not in x["jp"]
             and not x["jp"].rstrip().endswith(u"。")]
    canon = load_canon()
    print("candidates: %d | canon entries: %d" % (len(names), len(canon)))

    out, over, needs_review = {}, [], []
    n_canon = 0
    for x in names:
        jp = x["jp"]
        en = canon.get(norm(jp))
        src = "canon"
        if en:
            n_canon += 1
        if not en:
            en = translit(jp)
            src = "translit"
        if not en:
            continue
        nb = len(en.encode("cp932", "replace"))
        if nb > x["budget"]:
            over.append((jp, en, nb, x["budget"]))
            continue
        out[jp] = en
        if src == "translit" and any(u"一" <= c <= u"鿿" for c in jp):
            needs_review.append((jp, en))   # kanji names transliterate badly

    p = os.path.join(WORK, "analysis", "units_en.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("translated: %d  (canon %d, transliterated %d)"
          % (len(out), n_canon, len(out) - n_canon))
    print("over budget: %d" % len(over))
    print("KANJI names needing human review: %d" % len(needs_review))
    print("\nsample:")
    for jp, en in list(out.items())[:20]:
        print("   %-20s -> %s" % (jp, en))
    if needs_review:
        print("\nneeds review (kanji, transliteration unreliable):")
        for jp, en in needs_review[:20]:
            print("   %-20s -> %s" % (jp, en))
    if over:
        print("\nover budget:")
        for jp, en, nb, bud in over[:10]:
            print("   %-20s -> %-24s %d > %d" % (jp, en, nb, bud))
    print("\nwritten -> %s" % p)


if __name__ == "__main__":
    main()
