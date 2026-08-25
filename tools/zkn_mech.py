# -*- coding: utf-8 -*-
"""Build analysis/zkn_en.json from the mechanical + curated encyclopedia fields.

Covers everything that does not need a translator:
  HEIT / WEIT  fullwidth spec numbers -> ASCII  (１８．０ｍ -> 18.0m)
  PRDC / SRCE  series titles          -> zkn_names_en.SERIES
  WORD         glossary headwords     -> zkn_names_en.WORDS

Descriptions (DSCR/DSC2) and personal names are left alone here; they merge in
later from the translated set. Existing entries in zkn_en.json are preserved,
so this can be re-run after translations land without clobbering them.

Usage: zkn_mech.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_names_en import SERIES, WORDS

WORK = r"E:\Projects\SRW Z\_work"

# Fullwidth -> ASCII for the spec fields. '－－－' (unknown) becomes '---'.
_FW = {ord("０") + i: ord("0") + i for i in range(10)}
_FW.update({ord("．"): ord("."), ord("－"): ord("-"), ord("　"): ord(" "),
            ord("ｍ"): ord("m"), ord("ｔ"): ord("t"), ord("ｋ"): ord("k"),
            ord("ｇ"): ord("g"), ord("ｃ"): ord("c"), ord("？"): ord("?")})


def spec(t):
    out = t.translate(_FW)
    return out if all(ord(c) < 0x80 for c in out) else None


def main():
    jp = json.load(io.open(os.path.join(WORK, "analysis", "zkn_jp.json"),
                           encoding="utf-8"))
    p = os.path.join(WORK, "analysis", "zkn_en.json")
    en = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    n = {}
    skipped = []
    for key, ents in jp.items():
        dst = en.setdefault(key, {})
        for ri, e in ents.items():
            d = dst.setdefault(ri, {})
            for tag, t in e.items():
                if tag in d:
                    continue                       # never clobber a translation
                if tag in ("HEIT", "WEIT"):
                    v = spec(t)
                    if v is None:
                        skipped.append((key, ri, tag, t))
                        continue
                elif tag in ("PRDC", "SRCE"):
                    v = SERIES.get(t)
                elif tag == "WORD":
                    v = WORDS.get(t)
                else:
                    v = None
                if v:
                    d[tag] = v
                    n[key + "/" + tag] = n.get(key + "/" + tag, 0) + 1
    # drop empty records so the file stays readable
    for key in list(en):
        en[key] = {k: v for k, v in en[key].items() if v}
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(en, ensure_ascii=False, indent=1))
    for k in sorted(n):
        print("  %-9s %4d fields" % (k, n[k]))
    print("total %d fields -> %s" % (sum(n.values()), p))
    if skipped:
        print("spec fields left Japanese (unmapped glyph): %d" % len(skipped))
        for s in skipped[:5]:
            print("   ", s)


if __name__ == "__main__":
    main()
