# -*- coding: utf-8 -*-
"""Retry the stage rows missing2_deepseek.py did not land.

A first pass over 1,486 items left 566 with no answer (chunks the model dropped
or returned unparseable) and 151 over their byte budget. Both are recoverable:
smaller chunks fix the dropped ones, and restating the limit per item fixes most
overruns. Runs repeatedly until a pass adds nothing.

Usage: missing2_retry.py [rounds]
"""
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call, parse_obj, sanitize
from missing2_deepseek import SYSTEM

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 6
WORKERS = 8

STRICT = SYSTEM + """

CRITICAL: several earlier answers were REJECTED for exceeding the budget. Count
the characters of your English before answering. If it does not fit, shorten it -
drop adjectives, use a shorter synonym, abbreviate. An answer that overruns the
budget is thrown away and the line stays untranslated, which is worse than a
terse translation."""


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    a = os.path.join(WORK, "analysis")
    todo = json.load(io.open(os.path.join(a, "missing2_todo.json"), encoding="utf-8"))
    p = os.path.join(a, "missing2_en.json")
    out = json.load(io.open(p, encoding="utf-8"))
    api = open(KEYFILE).read().strip()

    for rnd in range(rounds):
        items = []
        for jp, locs in todo.items():
            if jp in out:
                continue
            i = 0
            while i < len(jp) and ord(jp[i]) < 0x20 and jp[i] != "\n":
                i += 1
            body = jp[i:]
            bud = min(x[3] for x in locs) - i
            if bud < 2 or not body.strip():
                continue
            items.append((jp, body, bud))
        if not items:
            break
        print("round %d: %d still missing" % (rnd + 1, len(items)))
        idx = {str(n): it for n, it in enumerate(items)}
        chunks = [items[i:i + CHUNK] for i in range(0, len(items), CHUNK)]
        base = {}
        for n, it in enumerate(items):
            base[it[0]] = str(n)

        def do(ch):
            lines = ["%s\t%d\t%s" % (base[jp], bud, body.replace("\n", "\\n"))
                     for jp, body, bud in ch]
            try:
                r = parse_obj(call(api, STRICT, "\n".join(lines)))
                return r if isinstance(r, dict) else {}
            except Exception:
                return {}

        got = {}
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for res in ex.map(do, chunks):
                got.update(res)
        added = 0
        for jp, body, bud in items:
            v = got.get(base[jp])
            if not isinstance(v, str) or not v.strip():
                continue
            v = sanitize(v.replace("\\n", "\n")).strip("\n")
            if len(v.encode("cp932", "replace")) <= bud:
                out[jp] = v
                added += 1
        print("  added %d (total %d)" % (added, len(out)))
        json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if not added:
            break
    print("final: %d translated of %d" % (len(out), len(todo)))


if __name__ == "__main__":
    main()
