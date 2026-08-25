# -*- coding: utf-8 -*-
"""Worklist for the 142 HEAD-TRUNCATED battle quotes.

These end with 」 but have no opening 「 ('に向け集中砲火だ！」', 'ﾌカタキだっ！」').
They are like that in the ORIGINAL file too - verified by parsing the untouched
extract - so they are a quirk of the game's string pool, not damage from our
rebuild. srvc_work.is_quote() requires a leading 「, so the whole pipeline has
always skipped them and they still ship Japanese.

They live in parsed blocks, so srvc.build() re-lays them out and length is free.

Writes analysis/srvc_head_work.json: [{"i": n, "jp": text, "n": slots}]
where "jp" keeps the trailing 」 (and any leading garbage byte) exactly, so the
apply step can match the string byte-for-byte.
"""
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN, CLOSE = u"「", u"」"


def jp(s):
    return sum(1 for c in s if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")


def main():
    data = open(os.path.join(WORK, "extracted", "BTL_SRVC.BIN"), "rb").read()
    seg = srvc.read_seg(
        open(os.path.join(WORK, "extracted", "BTL_SRVC.SEG"), "rb").read())
    blocks = srvc.parse(data, seg)

    counts = collections.Counter()
    for b in blocks:
        if not b.has_text:
            continue
        for s in b.strings:
            try:
                u = s.decode("cp932")
            except UnicodeDecodeError:
                continue
            if u.startswith(OPEN):
                continue
            if not u.rstrip(u"　 ").endswith(CLOSE):
                continue
            if jp(u) < 1:
                continue
            counts[u] += 1

    items = [{"i": i, "jp": u, "n": n}
             for i, (u, n) in enumerate(counts.most_common())]
    p = os.path.join(WORK, "analysis", "srvc_head_work.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

    print("head-truncated quotes: %d unique, %d slots"
          % (len(items), sum(x["n"] for x in items)))
    print("with real Japanese (>=2 chars): %d"
          % sum(1 for x in items if jp(x["jp"]) >= 2))
    print("written -> %s\n" % p)
    for x in items[:20]:
        print("  x%-3d %s" % (x["n"], json.dumps(x["jp"], ensure_ascii=False)))


if __name__ == "__main__":
    main()
