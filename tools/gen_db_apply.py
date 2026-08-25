# -*- coding: utf-8 -*-
"""Turn db_en.json (keyed by Japanese) into an OFFSET-keyed apply map.

COMPDATA 0..0x66380 is mostly binary structures; 448 of 1,112 "Japanese-looking"
strings there are noise. A string-keyed field_replace over that range would be
free to match inside binary, so bind every write to the exact offsets that
scope_remaining.py verified as real text.

Output: analysis/db_apply.json  {"offset": english}
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

todo = json.load(io.open(os.path.join(WORK, "analysis", "db_todo.json"),
                         encoding="utf-8"))
en_map = json.load(io.open(os.path.join(WORK, "analysis", "db_en.json"),
                           encoding="utf-8"))

out, over, miss = {}, [], 0
for x in todo:
    en = en_map.get(x["jp"])
    if not en:
        miss += 1
        continue
    nb = len(en.encode("cp932", "replace"))
    if nb > x["budget"]:
        over.append((x["offset"], x["jp"], en, nb, x["budget"]))
        continue
    out[str(x["offset"])] = en

p = os.path.join(WORK, "analysis", "db_apply.json")
with io.open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)

print("slots        : %d" % len(todo))
print("will write   : %d" % len(out))
print("no translation: %d" % miss)
print("over budget  : %d" % len(over))
for off, jp, en, nb, bud in over[:12]:
    print("   0x%05X %-12s -> %-24s %d > %d" % (off, jp, en, nb, bud))
print("\nwritten -> %s" % p)
