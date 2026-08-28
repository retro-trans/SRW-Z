# -*- coding: utf-8 -*-
"""Rank battle captions by how likely the english is WRONG, not just short.

The 0.8.48 entry already recorded why length alone fails: it "mostly surfaces
shouts where terse English is correct". And the two lines a player reported -

    「とっておきの荒技を見せてやる！」 -> "Show you a secret wild move!"
    「ダーリン、嬉しそう…！」         -> "Darling, so happy...!"

both have MORE english than the ratio expects, so no length test would ever
look at them. The second is not even awkward, it is wrong: 嬉しそう is "you
LOOK happy", said about someone else, and the english makes the speaker happy.

So these detectors look for MEANING that went missing, each one a class already
seen in this project:

  name-dropped   a katakana proper noun in the japanese with no plausible
                 counterpart in the english - the "Forgive me, Colonel" defect
                 where ランスロー vanished
  evidential     そう/ようだ/らしい/みたい dropped - "looks happy" became "is
                 happy". Changes WHO the sentence is about
  question       japanese asks (か？/の？) and the english does not
  negation       japanese negates (ない/ぬ/まい) and the english has no
                 negative
  counted        a number in the japanese that is absent from the english
  noterm         english has no terminal punctuation at all

Nothing here decides anything. It ranks, so a human reads the worst first.

Usage: caption_audit.py [--min N] [--out FILE]
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "caption_pairs.json")
KATA = re.compile(u"[ァ-ヴー]{3,}")
EVID = (u"そう", u"ようだ", u"らしい", u"みたい", u"っぽい")
NEG = (u"ない", u"ねえ", u"ぬ", u"まい", u"ません")
NEG_EN = re.compile(r"\b(no|not|n't|never|nothing|none|won|can|cannot|without)\b",
                    re.I)
NUM = re.compile(u"[0-9０-９]+")


def romaji_ish(k):
    """Very rough katakana -> latin initial, enough to ask 'is this name in the
    english at all'. Not a transliterator: it only has to avoid false alarms."""
    m = {u"ア": "a", u"イ": "i", u"ウ": "u", u"エ": "e", u"オ": "o",
         u"カ": "k", u"キ": "k", u"ク": "k", u"ケ": "k", u"コ": "k",
         u"サ": "s", u"シ": "s", u"ス": "s", u"セ": "s", u"ソ": "s",
         u"タ": "t", u"チ": "c", u"ツ": "t", u"テ": "t", u"ト": "t",
         u"ナ": "n", u"ニ": "n", u"ヌ": "n", u"ネ": "n", u"ノ": "n",
         u"ハ": "h", u"ヒ": "h", u"フ": "f", u"ヘ": "h", u"ホ": "h",
         u"マ": "m", u"ミ": "m", u"ム": "m", u"メ": "m", u"モ": "m",
         u"ヤ": "y", u"ユ": "y", u"ヨ": "y",
         u"ラ": "r", u"リ": "r", u"ル": "r", u"レ": "r", u"ロ": "r",
         u"ワ": "w", u"ガ": "g", u"ギ": "g", u"グ": "g", u"ゲ": "g",
         u"ゴ": "g", u"ザ": "z", u"ジ": "j", u"ズ": "z", u"ゼ": "z",
         u"ゾ": "z", u"ダ": "d", u"ヂ": "j", u"ヅ": "z", u"デ": "d",
         u"ド": "d", u"バ": "b", u"ビ": "b", u"ブ": "b", u"ベ": "b",
         u"ボ": "b", u"パ": "p", u"ピ": "p", u"プ": "p", u"ペ": "p",
         u"ポ": "p"}
    return m.get(k[0], "")


def audit(jp, en):
    why = []
    body = en.strip().strip('"')
    low = body.lower()

    for k in KATA.findall(jp):
        ini = romaji_ish(k)
        if ini and ini not in low:
            # a katakana word of 3+ kana whose first sound appears nowhere in
            # the english - most often a name that was dropped
            why.append("name-dropped(%s)" % k)
            break

    if any(e in jp for e in EVID) and not re.search(
            r"\b(seem|look|appear|must be|apparently|sound)", low):
        why.append("evidential")

    if (u"か？" in jp or u"の？" in jp or jp.rstrip(u"」！！").endswith(u"か")) \
            and "?" not in body:
        why.append("question")

    if any(n in jp for n in NEG) and not NEG_EN.search(low):
        why.append("negation")

    for num in NUM.findall(jp):
        if num not in body:
            why.append("counted(%s)" % num)
            break

    if body and body[-1] not in "!?.…,:;\"'":
        why.append("noterm")
    return why


def main():
    lim = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 2
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(ROOT, "analysis", "caption_audit.json"))
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]
    hits, tally = [], {}
    for p in pairs:
        why = audit(p["jp"], p["en"])
        for w in why:
            tally[w.split("(")[0]] = tally.get(w.split("(")[0], 0) + 1
        if len(why) >= lim:
            hits.append(dict(p, why=why))
    hits.sort(key=lambda x: -len(x["why"]))
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(hits, ensure_ascii=False, indent=0))
    print("pairs audited      : %d" % len(pairs))
    for k in sorted(tally, key=lambda x: -tally[x]):
        print("   %-14s %5d" % (k, tally[k]))
    print("flagged (>=%d signals): %d -> %s"
          % (lim, len(hits), os.path.relpath(out, ROOT)))


if __name__ == "__main__":
    main()
