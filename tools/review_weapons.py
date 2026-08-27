# -*- coding: utf-8 -*-
"""Flag weapon names that look mistranslated, for human review.

Checks, in rough order of how wrong they are:

  romaji      the "translation" is just the katakana romanised - the tokenizer
              fell through to kata_romaji instead of finding a real name
  japanese    kana or kanji still in the english
  digitsplit  a number broken by a space: 'M6 8', '20 0mm', '２２ ３５'
  dupword     the same word twice: 'Cannon Cannon'
  abbrev      still an artefact of the old byte budget (mixed-case run-ons)
  gloss       english that is a literal gloss where a series term exists
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from kata_romaji import romanize

KANA = re.compile(u"[\u3040-\u30ff\u4e00-\u9fff]")
FW = {chr(0xFF10 + i): str(i) for i in range(10)}


def fold(s):
    for k, v in FW.items():
        s = s.replace(k, v)
    return s.lower().replace(" ", "").replace("-", "").replace(".", "")


def main():
    pairs = json.load(open("analysis/weapon_review.json", encoding="utf-8"))
    flags = {}
    for p in pairs:
        jp, en = p["jp"], p["en"]
        f = []
        if KANA.search(en):
            f.append("japanese")
        r = romanize(u"".join(c for c in jp if u"\u30a0" <= c <= u"\u30ff"))
        if r and len(r) > 5 and fold(en).startswith(fold(r)[:max(6, len(fold(r)) - 2)]):
            f.append("romaji")
        e = fold(p["en"])
        if re.search(r"\d\s+\d", fold(en).replace("", "")) or re.search(r"[0-9\uff10-\uff19]\s+[0-9\uff10-\uff19]", en):
            f.append("digitsplit")
        w = [x.lower() for x in re.findall(r"[A-Za-z]+", en)]
        if any(w[i] == w[i + 1] for i in range(len(w) - 1)):
            f.append("dupword")
        if re.search(r"[a-z][A-Z]", en) or re.search(r"\b[A-Z][a-z]{0,2}\.", en):
            f.append("abbrev")
        if f:
            flags[p["off"]] = (jp, en, f)
    order = ["romaji", "japanese", "digitsplit", "dupword", "abbrev"]
    counts = {k: 0 for k in order}
    for _, (_, _, f) in flags.items():
        for k in f:
            counts[k] = counts.get(k, 0) + 1
    print("weapon entries: %d, flagged: %d\n" % (len(pairs), len(flags)))
    for k in order:
        print("  %-12s %d" % (k, counts.get(k, 0)))
    want = sys.argv[1] if len(sys.argv) > 1 else None
    if want:
        print("\n=== %s ===" % want)
        n = 0
        for off, (jp, en, f) in sorted(flags.items()):
            if want in f:
                print("  %-30r -> %r" % (jp, en))
                n += 1
        print("  (%d)" % n)


if __name__ == "__main__":
    main()
