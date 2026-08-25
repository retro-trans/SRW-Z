"""Scan every extracted file and rank by how much real Japanese text it holds.

Guards against the false-positive problem: random/compressed bytes decode as
rare kanji by chance. Real game text is dominated by kana and common kanji, so
we score the *kana ratio* and use it to separate signal from noise.
"""
import os
import sys
import glob
import math
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sjisscan import find_runs, entropy


def kana_ratio(text):
    """Fraction of chars that are hiragana/katakana/punctuation -- real
    Japanese prose runs high; random kanji noise runs near zero."""
    if not text:
        return 0.0
    good = sum(1 for ch in text
               if "぀" <= ch <= "ヿ"      # kana
               or "＀" <= ch <= "￯"      # fullwidth forms
               or ch in "、。「」・")
    return good / len(text)


def main(pattern):
    rows = []
    for path in sorted(glob.glob(pattern)):
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()
        ent = entropy(data[:4 * 1024 * 1024])
        runs = find_runs(data, min_chars=4)
        all_text = "".join(t for _, t in runs)
        kr = kana_ratio(all_text)
        # only count runs that look like real prose
        real = [(o, t) for o, t in runs if kana_ratio(t) >= 0.25]
        real_chars = sum(len(t) for _, t in real)
        rows.append((real_chars, os.path.basename(path), size, ent, kr, len(real)))

    rows.sort(reverse=True)
    print("%-28s %14s %7s %6s %7s %9s" % ("FILE", "SIZE", "ENTROPY", "KANA", "RUNS", "JP CHARS"))
    print("-" * 78)
    total = 0
    for chars, name, size, ent, kr, nruns in rows:
        if chars == 0:
            continue
        total += chars
        print("%-28s %14s %7.2f %6.2f %7d %9s"
              % (name, "{:,}".format(size), ent, kr, nruns, "{:,}".format(chars)))
    print("-" * 78)
    print("TOTAL JAPANESE CHARACTERS: %s" % "{:,}".format(total))


if __name__ == "__main__":
    main(sys.argv[1])
