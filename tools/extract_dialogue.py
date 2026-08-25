# -*- coding: utf-8 -*-
"""Dump a record's translatable dialogue rows as a compact worklist.

Usage: extract_dialogue.py <recN>  ->  analysis/rec00N_work.json
Row = {i, budget, jp}. Includes character dialogue (name+quote), scene
headers (〜...〜), and choice/monologue lines; EXCLUDES pure encyclopedia
blocks (>200 chars, no speaker) which are handled in a separate library
pass, and non-JP/system strings.
"""
import json
import os
import re
import sys

WORK = r"E:\Projects\SRW Z\_work"
JP = re.compile(u"[\u3040-\u30FF\u4E00-\u9FFF]")


def main():
    n = int(sys.argv[1])
    rows = json.load(open(os.path.join(WORK, "analysis", "rec%03d_script.json" % n),
                         encoding="utf-8"))
    out = []
    for i, r in enumerate(rows):
        t = r["text"]
        jpn = len(JP.findall(t))
        if jpn < 2:
            continue
        # dialogue / scene / choice heuristics
        is_dlg = ("\n" in t and ("「" in t or "（" in t or "『" in t)) \
            or t.startswith("　") or "〜" in t or t.startswith("「")
        if not is_dlg:
            continue
        if len(t) > 220 and "「" not in t and "」" not in t:
            continue  # encyclopedia block
        out.append({"i": i, "budget": r.get("budget", r["nbytes"]), "jp": t})
    p = os.path.join(WORK, "analysis", "rec%03d_work.json" % n)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print("rec%03d: %d translatable rows -> %s" % (n, len(out), p))


if __name__ == "__main__":
    main()
