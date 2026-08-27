# -*- coding: utf-8 -*-
"""Restore weapon names that the per-slot byte budget cut short.

The budget was never a property of the name - it was the length of the slot the
Japanese happened to occupy, enforced because each name is reached by an
absolute pointer and so could not be moved. tools/pool.py lifts that: the pool
is repacked and every pointer rewritten, so a name may be any length. What is
left is the real constraint - how wide the weapon list draws - hence DISPLAY_CAP.

A name is changed ONLY when it is provably a budget casualty. gen_weapons.py
produced the shipped name as fit(jp, translate(jp), budget); if recomputing that
reproduces exactly what shipped, and the unfitted form differs, the slot is the
only reason it was short - so the unfitted form is restored. If the shipped name
does NOT match, it was hand-edited after generation and is left alone. Without
that guard a regenerate silently reverts hand-work: 'Vascud Crisis' would go
back to the tokenizer's 'Basukudokuraishisu'.

gen_weapons.py also kept the SHORTEST fitted form when one Japanese name filled
several slots, so a single tight slot abbreviated it everywhere; keying the
output by pool offset instead of by name fixes that.

Usage: gen_weapons_full.py [--cap N]  -> analysis/weapons_full.json {"0x..": name}
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from gen_weapons import translate, fit
from patch import encode

DISPLAY_CAP = 24        # 'Sigma Breast Musou Sword' renders in the pick list
if "--cap" in sys.argv:
    DISPLAY_CAP = int(sys.argv[sys.argv.index("--cap") + 1])

ent = json.load(open("analysis/weapons_jp.json", encoding="utf-8"))
cur = json.load(open("analysis/weapons_en.json", encoding="utf-8"))

out, grew, handed, toowide = {}, [], 0, []
for x in ent:
    jp, off, budget = x["jp"], x["off"], x["budget"]
    shipped = cur.get(jp)
    if shipped is None:
        continue
    full = translate(jp)
    if not full:
        continue
    expect = fit(jp, full, budget)
    if expect != shipped:
        handed += 1                       # hand-edited later: do not touch
        continue
    if full == shipped:
        continue                          # never was cut short
    if len(encode(full, "menu")) > DISPLAY_CAP:
        toowide.append((jp, shipped, full))
        continue
    out["%#x" % off] = full
    grew.append((budget, shipped, full))

json.dump(out, open("analysis/weapons_full.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print("slots restored to their full name : %d" % len(out))
print("left alone (hand-edited after gen) : %d" % handed)
print("left alone (over the %d-col cap)   : %d" % (DISPLAY_CAP, len(toowide)))
seen = set()
for bud, a, b in sorted(grew, key=lambda r: -(len(r[2]) - len(r[1]))):
    if a in seen: continue
    seen.add(a)
    print("   budget %-3d %-20r -> %r" % (bud, a, b))
print("\nover cap, kept as shipped:")
for jp, a, b in toowide[:10]:
    print("   %-22r  (full form %r = %d cols)" % (a, b, len(encode(b, "menu"))))
