# -*- coding: utf-8 -*-
"""Fill encyclopedia name fields from names the project has ALREADY translated.

Nothing here is invented. Every name is resolved from analysis/name_source.json,
which merges:
  * COMPDATA JP->EN field pairs harvested by pairing the original record against
    our patched one at identical offsets (the pilot database stores surname and
    given name in SEPARATE fields, so this yields 兜->Kabuto, 甲児->Kouji, ... )
  * glossary.json (the script-translation glossary)
  * compdata_en.PILOTS / SHORT
  * akurasu_units.txt (JP|EN unit names)

That matters for consistency: the encyclopedia then spells every name exactly
the way the dialogue and unit lists already do.

Resolution order per value:
  1. exact hit in the source
  2. surname split - CHFN ends with CHNN, so prefix = surname; needs BOTH halves
     known. Emitted "Given Surname" (兜甲児 -> Kouji Kabuto).
  3. katakana split on the middle dot, all parts known.
Anything unresolved is left Japanese for the translation pass; this never
guesses a romanisation.

Usage: zkn_names_apply.py [--dry]
"""
import io
import json
import os
import sys

WORK = r"E:\Projects\SRW Z\_work"
DOT = "\u30fb"
# CHFN is the full name and pairs with CHNN (the short form) for the split.
# CHFN MUST RUN BEFORE PLTN: a robot's PLTN is the same string as some
# character's CHFN (70 of 76 of them), but PLTN has no short form of its own to
# split on, so it can only be resolved by reusing what CHFN worked out. Without
# this, Getter Dragon's description said "Ryouma Nagare" while the pilot field
# beside it still read 流竜馬.
FIELDS = [("RT", "RBTN", None), ("PT", "CHFN", "CHNN"),
          ("PT", "CHNN", None), ("RT", "PLTN", None),
          ("PT", "ACTR", None)]      # voice actors: real people, romanised only


# Fullwidth alphanumerics -> ASCII. The game data writes マジンガーＺ / ガザＣ with
# FULLWIDTH latin, while the akurasu unit list writes マジンガーZ with half-width,
# so an exact-match lookup silently missed a whole class of unit names.
_FW = {}
for _a, _b in ((0xFF21, ord("A")), (0xFF41, ord("a")), (0xFF10, ord("0"))):
    _n = 26 if _b != ord("0") else 10
    _FW.update({_a + i: _b + i for i in range(_n)})


def norm(s):
    return s.translate(_FW)


def build_index(src):
    """Normalised lookup, without clobbering exact keys."""
    idx = {}
    for k, v in src.items():
        idx.setdefault(norm(k), v)
    return idx


def resolve(src, full, short=None, idx=None):
    def get(k):
        if k in src:
            return src[k]
        return idx.get(norm(k)) if idx else None

    v = get(full)
    if v:
        return v
    if short and full.endswith(short) and full != short:
        sur = full[:-len(short)].rstrip(DOT)
        a, b = get(sur), get(short)
        if a and b:
            return "%s %s" % (b, a)
    if DOT in full:
        parts = [p for p in full.split(DOT) if p]
        got = [get(p) for p in parts]
        if all(got):
            return " ".join(got)
    return None


def main():
    dry = "--dry" in sys.argv
    a = os.path.join(WORK, "analysis")
    jp = json.load(io.open(os.path.join(a, "zkn_jp.json"), encoding="utf-8"))
    src = json.load(io.open(os.path.join(a, "name_source.json"), encoding="utf-8"))
    p = os.path.join(a, "zkn_en.json")
    en = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    # Seed from names already written on a previous run, so PLTN can reuse a
    # CHFN resolution even when CHFN itself is skipped as already-done.
    for key, ents in en.items():
        for ri, f in ents.items():
            for tag in ("CHFN", "RBTN"):
                j = jp.get(key, {}).get(ri, {}).get(tag)
                if j and tag in f:
                    src.setdefault(j, f[tag])
    idx = build_index(src)
    stats = {}
    for key, tag, pair in FIELDS:
        n = miss = 0
        for ri, e in jp[key].items():
            if tag not in e:
                continue
            d = en.setdefault(key, {}).setdefault(ri, {})
            if tag in d:
                continue
            v = resolve(src, e[tag], e.get(pair) if pair else None, idx)
            if v:
                d[tag] = v
                n += 1
                # Feed every full name we work out back into the source, so the
                # pilot fields can reuse the character records' resolutions.
                src.setdefault(e[tag], v)
                idx.setdefault(norm(e[tag]), v)
            else:
                miss += 1
        stats[key + "/" + tag] = (n, miss)
    for k, (n, miss) in stats.items():
        print("  %-9s filled %-4d  left Japanese %-4d" % (k, n, miss))
    print("total filled: %d" % sum(s[0] for s in stats.values()))
    if dry:
        print("(dry run)")
        return
    for key in list(en):
        en[key] = {k: v for k, v in en[key].items() if v}
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(en, ensure_ascii=False, indent=1))
    print("-> %s" % p)


if __name__ == "__main__":
    main()
