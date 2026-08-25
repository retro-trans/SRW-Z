# -*- coding: utf-8 -*-
"""Katakana -> Hepburn romaji (for weapon-name proper nouns)."""

BASE = {
    "ア": "a", "イ": "i", "ウ": "u", "エ": "e", "オ": "o",
    "カ": "ka", "キ": "ki", "ク": "ku", "ケ": "ke", "コ": "ko",
    "ガ": "ga", "ギ": "gi", "グ": "gu", "ゲ": "ge", "ゴ": "go",
    "サ": "sa", "シ": "shi", "ス": "su", "セ": "se", "ソ": "so",
    "ザ": "za", "ジ": "ji", "ズ": "zu", "ゼ": "ze", "ゾ": "zo",
    "タ": "ta", "チ": "chi", "ツ": "tsu", "テ": "te", "ト": "to",
    "ダ": "da", "ヂ": "ji", "ヅ": "zu", "デ": "de", "ド": "do",
    "ナ": "na", "ニ": "ni", "ヌ": "nu", "ネ": "ne", "ノ": "no",
    "ハ": "ha", "ヒ": "hi", "フ": "fu", "ヘ": "he", "ホ": "ho",
    "バ": "ba", "ビ": "bi", "ブ": "bu", "ベ": "be", "ボ": "bo",
    "パ": "pa", "ピ": "pi", "プ": "pu", "ペ": "pe", "ポ": "po",
    "マ": "ma", "ミ": "mi", "ム": "mu", "メ": "me", "モ": "mo",
    "ヤ": "ya", "ユ": "yu", "ヨ": "yo",
    "ラ": "ra", "リ": "ri", "ル": "ru", "レ": "re", "ロ": "ro",
    "ワ": "wa", "ヲ": "o", "ン": "n", "ヴ": "vu",
}
SMALL = {
    "ャ": "ya", "ュ": "yu", "ョ": "yo",
    "ァ": "a", "ィ": "i", "ゥ": "u", "ェ": "e", "ォ": "o",
}


def romanize(kata):
    out = ""
    i = 0
    n = len(kata)
    while i < n:
        c = kata[i]
        nxt = kata[i + 1] if i + 1 < n else ""
        if c == "ッ":
            # geminate: double the next consonant
            if nxt in BASE and BASE[nxt][0] not in "aiueon":
                out += BASE[nxt][0]
            i += 1
            continue
        if c == "ー":
            i += 1
            continue
        if nxt in SMALL and c in BASE:
            b = BASE[c]
            s = SMALL[nxt]
            if s in ("ya", "yu", "yo") and b.endswith("i"):
                if b in ("shi", "ji", "chi"):
                    out += b[:-1] + s[1:]
                else:
                    out += b[0] + s
            else:
                out += b[:-1] + s
            i += 2
            continue
        out += BASE.get(c, "")
        i += 1
    return out.capitalize()
