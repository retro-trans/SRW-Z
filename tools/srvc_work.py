# -*- coding: utf-8 -*-
"""Build the battle-voice worklist from BTL/SRVC.BIN.

SRVC's string pool holds non-text records alongside the dialogue, and some of
them decode as kanji in cp932 (e.g. 9e 68 04 0c 1f 0a -> '柯\\x04\\x0c\\x1f\\n'),
so "contains a kanji" is NOT a safe filter - it would drag binary into the
translator and corrupt the file. Real battle quotes are cp932 text with no C0
control bytes that open with the quote mark 「. That test yields 25,806 unique
lines across 60,827 slots; everything else is passed through untouched.

Lines are deduplicated: one translation fills every slot that repeats it.

The line-break marker inside these strings is a LITERAL backslash-n (two
characters), not 0x0A, and the game's own text pads it as `　\\n　`. The padding
is stripped here and re-applied as a plain marker so the model only has to deal
with `\\n`.

Writes analysis/srvc_work.json: [{"i": n, "jp": inner, "n": slots}, ...],
most-repeated first so an interrupted run has covered the highest-value lines.
"""
import collections
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc

WORK = r"E:\Projects\SRW Z\_work"
CTRL = re.compile(rb"[\x00-\x08\x0b-\x1f]")
OPEN, CLOSE = u"\u300c", u"\u300d"          # 「 」
IDEO = u"\u3000"                            # fullwidth space


def load_blocks():
    data = open(os.path.join(WORK, "extracted", "BTL_SRVC.BIN"), "rb").read()
    seg = srvc.read_seg(
        open(os.path.join(WORK, "extracted", "BTL_SRVC.SEG"), "rb").read())
    return data, seg, srvc.parse(data, seg)


def is_quote(raw):
    """True for a real battle-voice line (not a binary record)."""
    if CTRL.search(raw):
        return False
    try:
        u = raw.decode("cp932")
    except UnicodeDecodeError:
        return False
    return u.startswith(OPEN)


def inner(u):
    """Strip the 「」 wrapper and the padding around each \\n break."""
    if u.startswith(OPEN):
        u = u[1:]
    if u.endswith(CLOSE):
        u = u[:-1]
    u = re.sub(IDEO + r"*\\n" + IDEO + r"*", r"\\n", u)
    return u.strip(IDEO)


def main():
    data, seg, blocks = load_blocks()
    counts = collections.Counter()
    for b in blocks:
        if not b.has_text:
            continue
        for s in b.strings:
            if is_quote(s):
                counts[s.decode("cp932")] += 1

    items, seen = [], {}
    for u, n in counts.most_common():
        t = inner(u)
        if not t:
            continue
        if t in seen:                       # different padding, same words
            items[seen[t]]["n"] += n
            continue
        seen[t] = len(items)
        items.append({"i": len(items), "jp": t, "n": n})

    out = os.path.join(WORK, "analysis", "srvc_work.json")
    json.dump(items, io.open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("%s unique lines -> %s" % ("{:,}".format(len(items)), out))
    print("covering %s slots, %s JP chars"
          % ("{:,}".format(sum(x["n"] for x in items)),
             "{:,}".format(sum(len(x["jp"]) for x in items))))
    print("with a line break: %s"
          % "{:,}".format(sum(1 for x in items if "\\n" in x["jp"])))


if __name__ == "__main__":
    main()
