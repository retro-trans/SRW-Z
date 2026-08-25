# -*- coding: utf-8 -*-
"""Validate the passthrough translations and emit the override map.

Checks each entry actually fits its slot and contains no Japanese, so a
half-finished translation cannot quietly ship as Japanese again.

Writes analysis/passthrough_en.json.
"""
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import apply_stage as A
from passthrough_en import PASSTHROUGH, FINAL

JP = re.compile(r"[぀-ヿ一-鿿]+")


def main():
    items = json.load(io.open(os.path.join(WORK, "analysis", "passthrough_jp.json"),
                              encoding="utf-8"))
    todo = {"%d:%d" % (x["rec"], x["row"]): x for x in items if x["identical"]}

    out, bad, missing = {}, [], []
    cache = {}
    for key, x in sorted(todo.items()):
        en = PASSTHROUGH.get(key)
        if en is None:
            missing.append(x)
            continue
        left = JP.findall(en)
        if left:
            bad.append((key, "still Japanese: %s" % left, en))
            continue
        n = x["rec"]
        if n not in cache:
            p = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
            cache[n] = bytearray(open(p, "rb").read())
        orig = cache[n]
        off, bud = x["offset"], x["budget"]
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        is_dlg = ("\n" in en and len(first) <= 15
                  and not first.endswith((".", "!", "?")))
        enc = bytes(orig[off:off + lead]) + A.pencode(en, "ascii" if is_dlg else "menu")
        if len(enc) > bud:
            bad.append((key, "OVER %d > %d" % (len(enc), bud), en))
            continue
        out[key] = en

    # rows that had no translation at all - validated the same way
    for key, en in FINAL.items():
        rec, row = (int(v) for v in key.split(":"))
        js = os.path.join(WORK, "analysis", "rec%03d_script.json" % rec)
        rows = json.load(io.open(js, encoding="utf-8"))
        r = rows[row]
        if rec not in cache:
            dp = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % rec)
            cache[rec] = bytearray(open(dp, "rb").read())
        orig = cache[rec]
        off, bud = r["offset"], r["budget"]
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        is_dlg = ("\n" in en and len(first) <= 15
                  and not first.endswith((".", "!", "?")))
        enc = bytes(orig[off:off + lead]) + A.pencode(en, "ascii" if is_dlg else "menu")
        if JP.findall(en):
            bad.append((key, "still Japanese", en))
        elif len(enc) > bud:
            bad.append((key, "OVER %d > %d" % (len(enc), bud), en))
        else:
            out[key] = en

    p = os.path.join(WORK, "analysis", "passthrough_en.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("passthrough rows : %d" % len(todo))
    print("translated & fit : %d" % len(out))
    print("problems         : %d" % len(bad))
    print("not yet written  : %d" % len(missing))
    for k, why, en in bad[:20]:
        print("   %-12s %s" % (k, why))
        print("      %r" % en[:72])
    if missing:
        import collections
        c = collections.Counter(x["rec"] for x in missing)
        print("\nremaining by record: %s" % dict(sorted(c.items())))
    print("\nwritten -> %s" % p)


if __name__ == "__main__":
    main()
