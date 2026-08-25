# -*- coding: utf-8 -*-
"""Tighten the 231 scenario lines whose English overruns its byte budget.

apply_record SKIPS an over-budget row, so the original Japanese ships. Most are
only 1-6 bytes over, and meaning-preserving rewrites recover that.

Rules are conservative and reversible in meaning:
  - '...' -> cp932 '…' (3 bytes -> 2), the game's own glyph
  - standard contractions ('do not' -> "don't")
  - collapse double spaces / space before newline

Writes analysis/tighten_en.json {"rec:row": english}, which apply_stage prefers
over the T entry. Deliberately NOT rewriting the 167 recNNN_en.py files: an
override map keeps the edit reviewable in one place and avoids mass-rewriting
source that is keyed by row index.
"""
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import apply_stage as A

try:
    from tighten_manual import MANUAL
except ImportError:
    MANUAL = {}

ELL = u"…"
CONTRACT = [
    ("do not", "don't"), ("Do not", "Don't"),
    ("cannot", "can't"), ("Cannot", "Can't"),
    ("can not", "can't"),
    ("will not", "won't"), ("Will not", "Won't"),
    ("is not", "isn't"), ("are not", "aren't"),
    ("was not", "wasn't"), ("were not", "weren't"),
    ("have not", "haven't"), ("has not", "hasn't"),
    ("had not", "hadn't"), ("did not", "didn't"),
    ("does not", "doesn't"), ("could not", "couldn't"),
    ("would not", "wouldn't"), ("should not", "shouldn't"),
    ("must not", "mustn't"),
    ("I am ", "I'm "), ("I will ", "I'll "), ("I have ", "I've "),
    ("we are ", "we're "), ("We are ", "We're "),
    ("we will ", "we'll "), ("We will ", "We'll "),
    ("you are ", "you're "), ("You are ", "You're "),
    ("you will ", "you'll "), ("You will ", "You'll "),
    ("they are ", "they're "), ("They are ", "They're "),
    ("they will ", "they'll "), ("They will ", "They'll "),
    ("it is ", "it's "), ("It is ", "It's "),
    ("that is ", "that's "), ("That is ", "That's "),
    ("there is ", "there's "), ("There is ", "There's "),
    ("he is ", "he's "), ("He is ", "He's "),
    ("she is ", "she's "), ("She is ", "She's "),
    ("let us ", "let's "), ("Let us ", "Let's "),
]


def encoded_len(en, orig, off, budget):
    lead = 0
    while (lead < 4 and off + lead < len(orig)
           and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
        lead += 1
    first = en.split("\n", 1)[0].rstrip()
    is_dlg = ("\n" in en and len(first) <= 15
              and not first.endswith((".", "!", "?")))
    return len(bytes(orig[off:off + lead])
               + A.pencode(en, "ascii" if is_dlg else "menu"))


# Second tier: still meaning-preserving, but visible in the text. Applied only
# after tier 1 fails, cheapest first.
TITLES = [
    ("Lieutenant ", "Lt. "), ("Commander ", "Cmdr. "),
    ("Captain ", "Capt. "), ("Professor ", "Prof. "),
    ("Doctor ", "Dr. "), ("Sergeant ", "Sgt. "),
    ("Colonel ", "Col. "), ("General ", "Gen. "),
    ("Admiral ", "Adm. "), ("President ", "Pres. "),
    ("Chairman ", "Chmn. "),
]
WORDS = [
    ("towards", "toward"), ("amongst", "among"),
    ("in order to ", "to "), ("is able to ", "can "),
    ("are able to ", "can "), ("has been ", "was "),
    ("have been ", "were "), ("going to ", "gonna "),
    ("because ", "since "), ("However, ", "But "),
    ("Therefore, ", "So "), ("immediately", "at once"),
    (" as well", " too"), ("everything", "it all"),
]


def tighten(en):
    steps = []
    cur = en
    # 1. contractions
    for a, b in CONTRACT:
        if a in cur:
            cur = cur.replace(a, b)
            steps.append(a)
    # 2. whitespace
    cur = re.sub(r"[ \t]{2,}", " ", cur)
    cur = re.sub(r"[ \t]+\n", "\n", cur)
    yield cur, list(steps)
    # 3. ellipses, one at a time (each saves a byte)
    while "..." in cur:
        cur = cur.replace("...", ELL, 1)
        steps.append("...->…")
        yield cur, list(steps)
    # 4. '..' is used as an ellipsis all through the earlier translation waves;
    #    a single '.' reads the same and saves a byte each
    while ".." in cur:
        cur = cur.replace("..", ".", 1)
        steps.append("..->.")
        yield cur, list(steps)
    # 5. ranks and titles
    for a, b in TITLES:
        if a in cur:
            cur = cur.replace(a, b)
            steps.append(a.strip())
            yield cur, list(steps)
    # 6. wordier phrases
    for a, b in WORDS:
        if a in cur:
            cur = cur.replace(a, b)
            steps.append(a.strip())
            yield cur, list(steps)


def main():
    items = json.load(io.open(os.path.join(WORK, "analysis", "overbudget_jp.json"),
                              encoding="utf-8"))
    fixed, residue = {}, []
    cache = {}
    for x in items:
        n = x["rec"]
        if n not in cache:
            p = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
            cache[n] = bytearray(open(p, "rb").read())
        orig = cache[n]
        key = "%d:%d" % (n, x["row"])
        # hand-written rewrite wins over the mechanical ladder
        if key in MANUAL:
            cand = MANUAL[key]
            if encoded_len(cand, orig, x["offset"], x["budget"]) <= x["budget"]:
                fixed[key] = cand
                continue
            # recompute the deficit against the MANUAL text, else the residue
            # report shows the original row's over-count and misleads the next
            # editing pass
            need = encoded_len(cand, orig, x["offset"], x["budget"])
            x = dict(x, en=cand, need=need, over=need - x["budget"],
                     note="manual still over")
        got = None
        for cand, steps in tighten(x["en"]):
            if encoded_len(cand, orig, x["offset"], x["budget"]) <= x["budget"]:
                got = (cand, steps)
                break
        if got:
            fixed["%d:%d" % (n, x["row"])] = got[0]
        else:
            residue.append(x)

    p = os.path.join(WORK, "analysis", "tighten_en.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(fixed, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("over-budget rows       : %d" % len(items))
    print("fixed automatically    : %d" % len(fixed))
    print("still need hand editing: %d" % len(residue))
    print("\nexamples fixed:")
    for k in list(fixed)[:8]:
        print("   %-12s %r" % (k, fixed[k][:64]))
    print("\nresidue (need real rewrites), worst first:")
    for x in sorted(residue, key=lambda z: -z["over"])[:15]:
        print("   rec%03d row %-4d +%d bytes (budget %d)"
              % (x["rec"], x["row"], x["over"], x["budget"]))
        print("      %r" % x["en"][:74])
    p2 = os.path.join(WORK, "analysis", "tighten_residue.json")
    with io.open(p2, "w", encoding="utf-8") as f:
        json.dump(residue, f, ensure_ascii=False, indent=1)
    print("\nwritten -> %s\n           %s" % (p, p2))


if __name__ == "__main__":
    main()
