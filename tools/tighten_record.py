# -*- coding: utf-8 -*-
"""Auto-tighten over-budget dialogue rows in a recNNN_en.py file.

Applies safe, meaning-preserving shortenings (contractions, filler removal,
phrase compaction) to any row whose cp932 byte length exceeds its budget,
re-checking after each substitution. Rewrites the file. Reports any rows it
could not get under budget for manual attention.

Usage: tighten_record.py <N> [<N> ...]
"""
import importlib.util
import json
import os
import re
import sys

WORK = r"E:\Projects\SRW Z\_work"

# ordered: cheap/safe first
SUBS = [
    ("  ", " "),
    (" - ", "-"),
    ("...", ".."),
    ("cannot", "can't"), ("Cannot", "Can't"),
    (" will ", "'ll "), (" would ", "'d "),
    ("I am ", "I'm "), ("you are ", "you're "), ("You are ", "You're "),
    ("we are ", "we're "), ("We are ", "We're "),
    ("they are ", "they're "), ("They are ", "They're "),
    ("that is ", "that's "), ("That is ", "That's "),
    ("it is ", "it's "), ("It is ", "It's "),
    ("do not ", "don't "), ("Do not ", "Don't "),
    ("does not ", "doesn't "), ("did not ", "didn't "),
    ("is not ", "isn't "), ("are not ", "aren't "),
    ("was not ", "wasn't "), ("were not ", "weren't "),
    ("have not ", "haven't "), ("has not ", "hasn't "),
    ("will not ", "won't "), ("would not ", "wouldn't "),
    ("could not ", "couldn't "), ("should not ", "shouldn't "),
    (" really ", " "), (" just ", " "), (" very ", " "),
    (" quite ", " "), (" actually ", " "), (" simply ", " "),
    (" even ", " "), (" only ", " "), (" also ", " "),
    (" right now", " now"), (" as well", ""),
    (" of them", ""), (" of course", ""),
    ("More importantly, ", ""), ("For now, ", ""),
    ("Understood", "Roger"), ("understood", "got it"),
    (" a little ", " a bit "), (" perhaps ", " maybe "),
    (" because ", " since "), (" however ", " but "),
    (" Federation", " Fed"), (" Representative", " Rep"),
    ("New Fed", "N.Fed"),
    (" something ", " something"), ("  ", " "),
]


def bl(s):
    return len(s.encode("cp932"))


def tighten(text, budget):
    if bl(text) <= budget:
        return text
    cur = text
    for a, b in SUBS:
        if bl(cur) <= budget:
            break
        if a in cur:
            cur = cur.replace(a, b)
    cur = re.sub(r" +", " ", cur)
    cur = re.sub(r" +\n", "\n", cur)
    return cur


def process(n):
    p = os.path.join(WORK, "tools", "rec%03d_en.py" % n)
    spec = importlib.util.spec_from_file_location("m%d" % n, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    rows = json.load(open(os.path.join(WORK, "analysis", "rec%03d_work.json" % n),
                         encoding="utf-8"))
    budget = {r["i"]: r["budget"] for r in rows}
    fixed, still = 0, []
    for i in list(m.T):
        if i in budget and bl(m.T[i]) > budget[i]:
            new = tighten(m.T[i], budget[i])
            if bl(new) <= budget[i]:
                m.T[i] = new
                fixed += 1
            else:
                m.T[i] = new  # keep the shorter version anyway
                still.append(i)
    lines = ["# -*- coding: utf-8 -*-",
             '"""Stage record %d dialogue."""' % n, "", "T = {"]
    for k in sorted(m.T):
        lines.append("    %d: %r," % (k, m.T[k]))
    lines.append("}")
    open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("rec%03d: auto-fixed %d, still over %d %s" % (n, fixed, len(still), still))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(int(a))
