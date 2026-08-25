# -*- coding: utf-8 -*-
"""Retry the battle lines srvc_deepseek could not land.

Nearly all of the holdouts were REJECTED rather than lost: the English ran past
48 columns on a display line, and the model kept returning the same too-long
phrasing on each retry because nothing told it why the answer was thrown away.
This pass states the limit explicitly, offers the 3-line allowance as the escape
hatch, and shrinks the chunk so a single bad item cannot take its neighbours
down with it.

Usage: srvc_retry.py [rounds]
"""
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call
from srvc_deepseek import (SYSTEM, MAXCOL, MAXLINES, bad, norm, parse_map,
                           load_gloss, chunk_gloss)

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 4
WORKERS = 8

STRICT = SYSTEM + """

CRITICAL - PREVIOUS ANSWERS FOR THESE LINES WERE REJECTED FOR BEING TOO LONG.
Count the characters. Every display line must be at most %d characters. You may
use up to %d display lines separated by a literal backslash-n. If it still does
not fit, SHORTEN THE ENGLISH - cut adjectives, use a shorter synonym, drop
anything the shout does not need. A line that overruns is discarded and stays
Japanese in the game, which is far worse than a terse translation.""" % (
    MAXCOL, MAXLINES)


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))
    outp = os.path.join(WORK, "analysis", "srvc_en.json")
    out = json.load(io.open(outp, encoding="utf-8"))
    gloss = load_gloss()
    api = open(KEYFILE).read().strip()
    lock = threading.Lock()

    for rnd in range(rounds):
        todo = [x for x in items if str(x["i"]) not in out]
        if not todo:
            break
        print("round %d: %s missing" % (rnd + 1, "{:,}".format(len(todo))))
        chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
        added = [0]

        def do(ch):
            g = chunk_gloss(gloss, [x["jp"] for x in ch])
            user = ""
            if g:
                user += ("GLOSSARY (use these spellings exactly):\n" +
                         "\n".join(g) + "\n\n")
            user += "Translate each line. id<TAB>japanese\n"
            user += "\n".join("%d\t%s" % (x["i"], x["jp"]) for x in ch)
            try:
                r = parse_map(call(api, STRICT, user))
            except Exception:
                r = {}
            got = {}
            for x in ch:
                v = r.get(str(x["i"]))
                if isinstance(v, str):
                    v = norm(v)
                    if not bad(v):
                        got[str(x["i"])] = v
            with lock:
                out.update(got)
                added[0] += len(got)

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(out, io.open(outp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("  added %s (total %s)"
              % ("{:,}".format(added[0]), "{:,}".format(len(out))))
        if not added[0]:
            break

    left = [x for x in items if str(x["i"]) not in out]
    print("final: %s of %s translated, %s still Japanese"
          % ("{:,}".format(len(out)), "{:,}".format(len(items)),
             "{:,}".format(len(left))))


if __name__ == "__main__":
    main()
