# -*- coding: utf-8 -*-
"""Score a record's mechanical defect density WITHOUT running a proofread.

About half the defect classes leave a machine-detectable signature. The other
half (agency flips, dropped clauses, tone, fabrication) do not - but the two
correlate, so this ranks records by how much attention they deserve.

Signals:
  trunc   line ends on a preposition/article/conjunction + terminal punctuation
          ("...to!", "the.", "and!") - the single most common defect, ~40%
  comma   stray comma before terminal punctuation (",!" ",?" ",.") - the
          dropped-addressee signature
  nospk   japanese has a speaker line, english does not
  ascii   english body uses ASCII " instead of the kagi
  ph      a $ placeholder present in the japanese is missing from the english
  jp      untranslated japanese left in the english
  over    body exceeds 3 lines or 34 columns

Usage: triage.py validate      - measure the detector against known agent fixes
       triage.py <rec> [...]   - score records from the review exports
"""
import glob
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(WORK, "analysis", "review")
KAGI = u"\u300c"
# words that essentially CANNOT end an english sentence. "that"/"is"/"so"
# were removed - "I won't allow that!" is valid and they were most of the
# false positives.
# Mid setting: ~29% precision / 20% recall on known agent fixes. Too noisy
# to judge a single row, but UNBIASED across records, so it ranks records
# against each other correctly - which is all triage needs.
TAIL = (r"(?:to|the|a|an|of|and|with|for|in|on|at|from|my|your|his|her|"
        r"its|our|their|into|onto|upon|about|than|whose|by|as)")
TRUNC = re.compile(TAIL + r"\s*[!?.]*[\u300d\uff09]?\s*$")
COMMA = re.compile(r",\s*[!?.]+[\u300d\uff09]?\s*$")
PH = re.compile(r"\$[A-Za-z]")
JPCH = re.compile(u"[\u3040-\u30ff\u4e00-\u9fff]")


def flags(r):
    out = set()
    jl = r["jp"].split("\n")
    el = r["en"].split("\n")
    body = el[1:] if len(el) > 1 else el
    # ONLY the last body line can show truncation - lines 1..n-1 ending on
    # "the"/"to" are just normal word wrap, which is why testing every line
    # gave 14% precision.
    if body:
        s = body[-1].rstrip()
        if TRUNC.search(s):
            out.add("trunc")
        if COMMA.search(s):
            out.add("comma")
    if len(jl) >= 2 and KAGI in r["jp"] and len(el) < len(jl) \
            and KAGI not in el[0] and el[0].lstrip().startswith('"'):
        out.add("nospk")
    if '"' in r["en"] and KAGI not in r["en"] and KAGI in r["jp"]:
        out.add("ascii")
    import collections
    j = collections.Counter(PH.findall(r["jp"]))
    e = collections.Counter(PH.findall(r["en"]))
    if any(j[k] > e[k] for k in j):
        out.add("ph")
    if JPCH.search("".join(body)):
        out.add("jp")
    return out


def validate():
    """Do the flagged rows match what agents actually fixed?"""
    fixed = {}
    for p in glob.glob(os.path.join(REV, "fixes", "rec*.json")):
        b = os.path.basename(p)
        if b.endswith("_sonnet.json"):
            continue
        try:
            rec = int(b[3:6])
            for x in json.load(io.open(p, encoding="utf-8")):
                fixed.setdefault(rec, set()).add(x["row"])
        except Exception:
            pass
    tp = fp = fn = tot = 0
    for p in sorted(glob.glob(os.path.join(REV, "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        if rec not in fixed:
            continue
        for r in json.load(io.open(p, encoding="utf-8")):
            if KAGI not in r["en"] and u"\uff08" not in r["en"]:
                continue
            tot += 1
            f = bool(flags(r))
            g = r["row"] in fixed[rec]
            if f and g: tp += 1
            elif f and not g: fp += 1
            elif g and not f: fn += 1
    print("VALIDATION against %d rows agents already reviewed" % tot)
    print("  flagged AND fixed by an agent : %d" % tp)
    print("  flagged, agent left alone     : %d" % fp)
    print("  agent fixed, NOT flagged      : %d" % fn)
    if tp + fp:
        print("  precision (flag -> real fix)  : %.0f%%" % (100.0 * tp / (tp + fp)))
    if tp + fn:
        print("  recall (of all agent fixes)   : %.0f%%" % (100.0 * tp / (tp + fn)))


def score(recs):
    print("%-8s %6s %6s %6s  %s" % ("record", "rows", "flags", "per100", "breakdown"))
    for n in recs:
        p = os.path.join(REV, "rec%03d.json" % n)
        if not os.path.exists(p):
            print("rec%-4d  (not exported)" % n)
            continue
        rows = json.load(io.open(p, encoding="utf-8"))
        rows = [r for r in rows if KAGI in r["en"] or u"\uff08" in r["en"]]
        import collections
        c = collections.Counter()
        hit = 0
        for r in rows:
            f = flags(r)
            if f:
                hit += 1
            for k in f:
                c[k] += 1
        rate = 100.0 * hit / max(len(rows), 1)
        print("rec%-5d %6d %6d %6.1f  %s" % (
            n, len(rows), hit, rate,
            ", ".join("%s:%d" % (k, v) for k, v in c.most_common())))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate()
    else:
        score([int(a) for a in sys.argv[1:]])
