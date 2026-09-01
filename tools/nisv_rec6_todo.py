# -*- coding: utf-8 -*-
"""List the help-book paragraphs still needing english.

Usage: nisv_rec6_todo.py <lo> <hi>        sections lo..hi
       nisv_rec6_todo.py --stats          progress over the whole book
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(io.open(ROOT + "/analysis/help_jp.json", encoding="utf-8"))
en = json.load(io.open(ROOT + "/analysis/help_en.json", encoding="utf-8"))

if "--stats" in sys.argv:
    done = set()
    todo = {}
    for r in rows:
        (done if r["key"] in en else todo.setdefault(r["sec"], set())).add(r["key"])
    uniq = set(r["key"] for r in rows)
    print("%d of %d unique paragraphs translated (%.0f%%)"
          % (len(done), len(uniq), 100.0 * len(done) / len(uniq)))
    left = sum(r["chars"] for r in rows if r["key"] not in en)
    print("%d sections still have untranslated text, %d characters"
          % (len(todo), left))
    raise SystemExit(0)

lo, hi = int(sys.argv[1]), int(sys.argv[2])
seen = set()
for r in rows:
    if not (lo <= r["sec"] <= hi) or r["key"] in en or r["key"] in seen:
        continue
    seen.add(r["key"])
    print("%s |%d| %s" % (r["key"], r["sec"], r["jp"]))
