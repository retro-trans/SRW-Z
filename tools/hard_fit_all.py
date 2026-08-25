# -*- coding: utf-8 -*-
"""Meaning-preserving mechanical trim of the small over-budget stragglers in the
DeepSeek records. Applies a large set of safe contractions/shortenings; only if
STILL over does it drop a trailing word (last resort). Rewrites each record and
reports the residual. Zero API cost.

Usage: hard_fit_all.py            (all records in deepseek_review.json)
       hard_fit_all.py <N> ...    (specific records)
"""
import importlib.util as u
import json
import os
import re
import sys

WORK = r'E:\Projects\SRW Z\_work'
REV = WORK + r'\analysis\deepseek_review.json'


def bl(s):
    return len(s.encode('cp932', 'replace'))


# ordered, safe, meaning-preserving
SUBS = [
    ("  ", " "), ("...", ".."), ("!!!", "!!"), ("?!?", "?!"),
    ("cannot", "can't"), ("Cannot", "Can't"),
    (" I will ", " I'll "), (" you will ", " you'll "), (" we will ", " we'll "),
    (" they will ", " they'll "), (" he will ", " he'll "), (" she will ", " she'll "),
    (" it will ", " it'll "), (" that will ", " that'll "), (" this will ", " this'll "),
    (" would ", " 'd "), (" I am ", " I'm "), (" you are ", " you're "),
    (" we are ", " we're "), (" they are ", " they're "), (" that is ", " that's "),
    (" it is ", " it's "), (" there is ", " there's "), (" he is ", " he's "),
    (" she is ", " she's "), (" what is ", " what's "), (" who is ", " who's "),
    (" is not", " isn't"), (" are not", " aren't"), (" was not", " wasn't"),
    (" were not", " weren't"), (" do not", " don't"), (" does not", " doesn't"),
    (" did not", " didn't"), (" have not", " haven't"), (" has not", " hasn't"),
    (" had not", " hadn't"), (" will not", " won't"), (" would not", " wouldn't"),
    (" could not", " couldn't"), (" should not", " shouldn't"), (" cannot ", " can't "),
    (" I have ", " I've "), (" you have ", " you've "), (" we have ", " we've "),
    (" they have ", " they've "), (" I would ", " I'd "), (" you would ", " you'd "),
    (" let us ", " let's "),
    (" really ", " "), (" just ", " "), (" very ", " "), (" quite ", " "),
    (" actually ", " "), (" simply ", " "), (" even ", " "), (" only ", " "),
    (" also ", " "), (" truly ", " "), (" indeed ", " "), (" merely ", " "),
    (" somewhat ", " "), (" rather ", " "), (" perhaps ", " maybe "),
    (" right now", " now"), (" as well", ""), (" of course", ""), (" you know", ""),
    (" I mean ", " "), (" you see ", " "), (" at all", ""), (" anymore", ""),
    (" a little ", " a bit "), (" because ", " since "), (" however ", " but "),
    (" though ", " "), (" in order to ", " to "), (" as well as ", " and "),
    (" going to ", " gonna "), (" want to ", " wanna "), (" got to ", " gotta "),
    (" them", " 'em"), (" toward ", " to "), (" towards ", " to "),
    (" Federation", " Fed"), (" Representative", " Rep"), (" Commander", " Cmdr"),
    (" Lieutenant", " Lt"), (" Captain", " Capt"), (" General", " Gen"),
    (" Professor", " Prof"), (" Doctor ", " Dr "),
    (" everyone", " all"), (" everybody", " all"), (" something", " somethin'"),
    (" nothing", " nothin'"), (" the enemy", " the foe"),
]


def drop_word(s):
    """Remove the last word before trailing quote/punctuation. Last resort."""
    m = re.search(r'(\s+\S+?)([\s"\'.!?)\u3001\u3002]*)$', s)
    if not m or m.start(1) <= 0:
        return None
    return s[:m.start(1)] + m.group(2)


def hard_fit(s, budget):
    if bl(s) <= budget:
        return s
    cur = s
    for a, b in SUBS:
        if bl(cur) <= budget:
            break
        if a in cur:
            cur = cur.replace(a, b)
    cur = re.sub(r" +", " ", cur)
    cur = re.sub(r" +\n", "\n", cur).replace(" \"", "\"").replace("\n ", "\n")
    if bl(cur) <= budget:
        return cur if bl(cur) < bl(s) else s
    # last resort: drop trailing words (keep at least the speaker line + a couple words)
    guard = 0
    while bl(cur) > budget and guard < 8:
        nxt = drop_word(cur)
        if not nxt or nxt == cur:
            break
        cur = nxt
        guard += 1
    return cur if bl(cur) <= budget else (cur if bl(cur) < bl(s) else s)


def main():
    rev = json.load(open(REV))
    targets = [int(a) for a in sys.argv[1:]] or sorted(int(k[3:]) for k in rev)
    grand_before = grand_after = 0
    for n in targets:
        p = 'rec%03d_en.py' % n
        if not os.path.exists(p):
            continue
        s = u.spec_from_file_location('m%d' % n, p)
        m = u.module_from_spec(s)
        s.loader.exec_module(m)
        wk = {r['i']: r for r in json.load(
            open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))}
        before = [i for i in m.T if i in wk and bl(m.T[i]) > wk[i]['budget']]
        T = dict(m.T)
        for i in before:
            T[i] = hard_fit(T[i], wk[i]['budget'])
        after = [i for i in T if i in wk and bl(T[i]) > wk[i]['budget']]
        lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue (DeepSeek)."""' % n,
                 "", "T = {"]
        for k in sorted(T):
            lines.append("    %d: %r," % (k, T[k]))
        lines.append("}")
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        grand_before += len(before)
        grand_after += len(after)
        print("rec%03d: %d -> %d over" % (n, len(before), len(after)))
    print("TOTAL stragglers: %d -> %d" % (grand_before, grand_after))


if __name__ == "__main__":
    main()
