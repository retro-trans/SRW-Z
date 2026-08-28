# -*- coding: utf-8 -*-
"""Print paired captions for a human to read, one detector class at a time.

caption_audit.py ranks; this is what you actually read. It prints the japanese
beside our english with the worklist index, so anything wrong can be corrected
straight into analysis/srvc_en.json and applied with srvc_apply --free.

    caption_review.py evidential 0 30      class, start, count
    caption_review.py --all 0 40           every flagged pair, worst first
    caption_review.py --index 9288         one line, by worklist index

Reading a ranked list is not the same as reading the corpus, and the numbers
should be kept honest: about 2,000 of the 19,218 pairs carry a signal, and
roughly one flagged line in six turns out to be a real defect. The rest are
correct translations that happen to trip a pattern - the name detector in
particular fires on onomatopoeia (ベコベコ, キーキー) that look like names.

Usage: caption_review.py <class|--all|--index N> [start] [count]
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
from caption_audit import audit

PAIRS = os.path.join(ROOT, "analysis", "caption_pairs.json")
WORK = os.path.join(ROOT, "analysis", "srvc_work.json")


def load():
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]
    idx = {}
    for x in json.load(io.open(WORK, encoding="utf-8")):
        idx.setdefault(x["jp"], x["i"])
    return pairs, idx


def key(idx, jp):
    return idx.get(jp.strip(u"「」"), idx.get(jp, "?"))


def main():
    if not sys.argv[1:]:
        raise SystemExit(__doc__)
    pairs, idx = load()
    mode = sys.argv[1]

    if mode == "--index":
        want = sys.argv[2]
        for p in pairs:
            if str(key(idx, p["jp"])) == str(want):
                print("i=%s" % want)
                print("  JP %s" % p["jp"])
                print("  EN %s" % p["en"])
                print("  signals: %s" % ", ".join(audit(p["jp"], p["en"])) or "none")
                return 0
        print("no pair with index %s" % want)
        return 1

    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    out = []
    for p in pairs:
        why = audit(p["jp"], p["en"])
        if not why:
            continue
        if mode == "--all" or any(w.split("(")[0] == mode for w in why):
            out.append((len(why), key(idx, p["jp"]), p["jp"], p["en"], why))
    if mode == "--all":
        out.sort(key=lambda x: -x[0])
    print("%s: %d flagged" % (mode, len(out)))
    for n, (_s, ix, jp, en, why) in enumerate(out[start:start + count]):
        print("\n[%d] i=%s  %s" % (start + n, ix, ",".join(why)))
        print("  JP %s" % jp.replace(chr(10), " / ")[:64])
        print("  EN %s" % en.replace(chr(10), " / ")[:64])
    return 0


if __name__ == "__main__":
    sys.exit(main())
