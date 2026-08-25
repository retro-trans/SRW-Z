# -*- coding: utf-8 -*-
"""Audit every name in analysis/db_en.json against the corpus.

For each japanese name in the dictionary, find rows whose JP contains it and
collect the English tokens that look like the canonical name but are not it.
Near-misses (difflib ratio >= 0.6) are almost always misspellings; unrelated
words score far lower and are ignored.

This is the systematic version of the one-name-at-a-time scans: the dictionary
is the authority, so no majority-voting is involved.

Usage: audit_names.py [--rules]   (--rules prints TERMS entries to paste)
"""
import difflib
import glob
import io
import json
import os
import re
import sys
import collections

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    db = json.load(io.open(os.path.join(WORK, "analysis", "db_en.json"),
                           encoding="utf-8"))
    # only single-token latin names are safe to compare this way
    db = {j: e for j, e in db.items()
          if re.match(r"^[A-Z][A-Za-z'-]{2,}$", e) and len(j) >= 2}
    rows = []
    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        for r in json.load(io.open(p, encoding="utf-8")):
            rows.append((r["jp"], r["en"]))
    print("dictionary names usable: %d   corpus rows: %d\n" % (len(db), len(rows)))

    findings = []
    for jp, en in sorted(db.items()):
        good = 0
        bad = collections.Counter()
        for rjp, ren in rows:
            if jp not in rjp:
                continue
            toks = set(re.findall(r"\b[A-Z][A-Za-z'-]{2,}\b", ren))
            if en in toks:
                good += 1
                continue
            for t in toks:
                if t == en:
                    continue
                if difflib.SequenceMatcher(None, t.lower(), en.lower()).ratio() >= 0.6:
                    bad[t] += 1
        if bad and (good or sum(bad.values()) >= 2):
            findings.append((en, jp, good, bad))

    findings.sort(key=lambda f: -sum(f[3].values()))
    print("%-14s %-10s %6s  wrong variants" % ("CANONICAL", "JP", "right"))
    total = 0
    for en, jp, good, bad in findings:
        n = sum(bad.values())
        total += n
        print("%-14s %-10s %6d  %s" % (
            en, jp.encode("ascii", "backslashreplace").decode()[:10], good,
            ", ".join("%s:%d" % (k, v) for k, v in bad.most_common(5))))
    print("\ntotal rows carrying a non-canonical spelling: %d" % total)

    if "--rules" in sys.argv:
        print("\n--- candidate TERMS entries (same-or-shorter only) ---")
        for en, jp, good, bad in findings:
            for w, n in bad.most_common():
                if len(w) >= len(en):
                    print('    (u"%s", "%s", "%s"),' % (
                        jp.encode("unicode_escape").decode(), w, en))


main()
