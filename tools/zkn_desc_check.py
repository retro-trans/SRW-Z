# -*- coding: utf-8 -*-
"""Consistency check for agent-translated encyclopedia descriptions.

The risk with batch translation is not bad prose, it is a name spelled one way
here and another way in the dialogue. This flags any name where the description
text uses a spelling that differs from the one the rest of the patch already
ships (name_source.json), by looking for near-miss variants of every known
English name.

Usage: zkn_desc_check.py
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WORK = r"E:\Projects\SRW Z\_work"


def load_batches():
    """Auto-discover every zkn_desc_<x>.py exporting a DESC_* map.

    Hardcoding the batch list here once meant this check silently skipped two
    new batches and reported a stale, clean result.
    """
    out = {}
    here = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(here)):
        if not (f.startswith("zkn_desc_") and f.endswith(".py")):
            continue
        stem = f[:-3]
        if stem in ("zkn_desc_apply", "zkn_desc_en", "zkn_desc_check"):
            continue
        try:
            m = __import__(stem)
        except Exception as e:
            print("  WARNING: could not load %s (%s)" % (f, e))
            continue
        for k in dir(m):
            if k.startswith("DESC_"):
                for key, ents in getattr(m, k).items():
                    for ri, t in ents.items():
                        out["%s/%s" % (key, ri)] = t
    return out


def variants(name):
    """Plausible misspellings of a romanised Japanese name: long-vowel 'ou'/'o',
    'uu'/'u', doubled consonants, and 'a'/'u' slips (Kurama vs Kuruma)."""
    v = set()
    for a, b in (("ou", "o"), ("o", "ou"), ("uu", "u"), ("u", "uu"),
                 ("oo", "o"), ("o", "oo"), ("aa", "a"), ("a", "aa"),
                 ("ei", "e"), ("ee", "e")):
        if a in name.lower():
            i = name.lower().index(a)
            v.add(name[:i] + b + name[i + len(a):])
    # single-vowel slips inside the word
    for i in range(1, len(name) - 1):
        if name[i] in "aiueo":
            for c in "aiueo":
                if c != name[i]:
                    v.add(name[:i] + c + name[i + 1:])
    return {x for x in v if x != name and len(x) > 3}


def main():
    texts = load_batches()
    if not texts:
        print("no batch files yet")
        return
    src = json.load(io.open(os.path.join(WORK, "analysis", "name_source.json"),
                            encoding="utf-8"))
    # English names worth policing: multi-character, alphabetic, not generic
    canon = {v for v in src.values()
             if re.fullmatch(r"[A-Za-z][A-Za-z' -]{3,}", v or "")}
    blob = "\n".join(texts.values())
    words = set(re.findall(r"\b[A-Z][A-Za-z']{3,}\b", blob))
    hits = []
    for c in canon:
        for w in words:
            if w != c and w in variants(c):
                hits.append((c, w))
    print("distinct capitalised words in the batch text: %d" % len(words))
    if not hits:
        print("no near-miss spellings against the shipped glossary")
    for c, w in sorted(set(hits)):
        where = [k for k, t in texts.items() if re.search(r"\b%s\b" % re.escape(w), t)]
        print("  MISMATCH glossary %-18r batch uses %-18r  in %s"
              % (c, w, ", ".join(where[:6])))

    # CROSS-BATCH DRIFT. Two agents inventing different spellings for the same
    # name agree with the glossary (it has neither) but disagree with each
    # other - invisible to the check above. Zambot 3's 神 came out "Kami" in one
    # batch and "Jin" in another; canon is Jin.
    print("\ncross-batch: names appearing in some batches but near-missed in others")
    batch_of = {}
    for k in texts:
        batch_of[k] = k.split("/")[0]
    seen = {}
    for k, t in texts.items():
        for w in set(re.findall(r"\b[A-Z][A-Za-z']{3,}\b", t)):
            seen.setdefault(w, set()).add(k)
    flagged = 0
    words_l = sorted(seen)
    for i, a in enumerate(words_l):
        for b in words_l[i + 1:]:
            if b in variants(a) and not (seen[a] & seen[b]):
                # never co-occur in the same record: likely one name, two spellings
                if a in canon or b in canon:
                    continue          # already handled above
                print("  %-16r (%d recs) vs %-16r (%d recs)"
                      % (a, len(seen[a]), b, len(seen[b])))
                flagged += 1
    if not flagged:
        print("  none")


if __name__ == "__main__":
    main()
