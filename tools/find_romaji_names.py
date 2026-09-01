# -*- coding: utf-8 -*-
"""Find names still left as ROMAJI, judged from the english alone.

The pools cannot be paired by offset or by index - COMPDATA is repacked, so
the same address range holds 973 fields in our build and 789 in the virgin
disc, and aligning by entry index is what produced a fake off-by-one before.
So this does not try to pair anything: a transliteration is recognisable from
its own spelling.

A word is suspect when it segments cleanly into japanese syllables AND ends
the way kana force a word to end (a vowel, or n). "Sutoreitaretto" and
"Keruberosu" do; "Missile" and "Tomahawk" cannot, because English lets a word
end on a consonant cluster that kana cannot express.

Names that are genuinely japanese (Yata no Kagami, Jinba) also match, so the
output is a list to READ, not to apply blindly.

Usage: find_romaji_names.py <iso> [--all]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

CV = ["ky", "gy", "sh", "ch", "ts", "ny", "hy", "by", "py", "my", "ry", "j",
      "k", "g", "s", "z", "t", "d", "n", "h", "b", "p", "m", "y", "r", "w",
      "f", "v"]
VOW = "aeiou"

# real english words that happen to segment; not evidence of romaji
OK = set("""
sabotage karate ninja samurai tsunami kimono sumo tofu manga anime
banzai bonsai geisha haiku origami sake shogun sushi tempura zen
tomahawk katana naginata kunai shuriken bushido
""".split())


def segments(w):
    """True if w is a clean CV... romaji word ending in a vowel or n."""
    s = w.lower()
    if not s or not s.isalpha() or len(s) < 4:
        return False
    i = 0
    n = 0
    while i < len(s):
        if s[i] in VOW:                       # bare vowel
            i += 1
            n += 1
            continue
        # geminate: doubled consonant before a CV
        if (i + 1 < len(s) and s[i] == s[i + 1] and s[i] not in VOW
                and s[i] != "n"):
            i += 1
        hit = None
        for c in CV:
            if s.startswith(c, i):
                hit = c
                break
        if hit is None:
            return s[i:] == "n" and n >= 2    # trailing n is legal
        i += len(hit)
        if i < len(s) and s[i] in VOW:
            i += 1
            n += 1
            if i < len(s) and s[i] in VOW:    # long vowel / diphthong
                i += 1
        elif s[i:] == "":
            return False
        elif s[i] == "n" and i + 1 == len(s):
            i += 1
        else:
            return False
    return n >= 3


def suspect(name):
    words = [w for w in name.replace("-", " ").replace("(", " ")
             .replace(")", " ").replace(".", " ").split() if w.isalpha()]
    return [w for w in words
            if w.lower() not in OK and len(w) >= 5 and segments(w)]


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(1823000 * 2048)
    d = bytes(banlz.decompress_all(f.read(400 * 2048))[0][1])
    f.close()

    seen, hits = set(), []
    i = 0x60000
    while i < 0x76000:
        while i < 0x76000 and d[i] == 0:
            i += 1
        z = d.find(b"\x00", i)
        if z < 0 or z > 0x76000:
            break
        try:
            s = d[i:z].decode("cp932")
        except UnicodeDecodeError:
            s = None
        if s and s not in seen and any(ord(c) < 128 for c in s):
            seen.add(s)
            bad = suspect(s)
            if bad:
                hits.append((i, s, bad))
        i = z + 1

    print("%d distinct strings scanned, %d suspect" % (len(seen), len(hits)))
    for off, s, bad in hits:
        print("  %#08x  %-34s <- %s" % (off, s, ", ".join(bad)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
