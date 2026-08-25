# -*- coding: utf-8 -*-
"""Wrap translated encyclopedia descriptions and merge them into zkn_en.json.

Descriptions are stored UNWRAPPED in the batch files and wrapped here, so the
widths live in one place.

EACH SET HAS ITS OWN BOX WIDTH - measured from the Japanese, the widest line is
KW 50, PT 34, RT 54 columns. The character box is barely two thirds of the robot
one. Wrapping everything to a single width made character entries overflow, and
the renderer does NOT re-wrap: it draws the overflow on the next line ON TOP of
what is already there, which is what the in-game garbling looked like.

Line COUNT is not a constraint: the longest Japanese description runs to 63
lines, so the box scrolls.

DSC2 is the same text again (sometimes re-wrapped, sometimes extended). Where
the Japanese DSC2 matches DSCR ignoring line breaks, the English is copied into
it as well - otherwise DSC2 is left alone for its own translation.

Usage: zkn_desc_apply.py [--dry]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_desc_en import KW_DSCR

# Batch files written by the translation agents, each exporting one
# DESC_<X> = {"KW": {id: text}, "RT": {...}}. Auto-discovered so adding a batch
# needs no edit here; missing/failed ones are skipped so this runs mid-round.
BATCHES = []
_here = os.path.dirname(os.path.abspath(__file__))
for _f in sorted(os.listdir(_here)):
    if not (_f.startswith("zkn_desc_") and _f.endswith(".py")):
        continue
    _stem = _f[:-3]
    if _stem in ("zkn_desc_apply", "zkn_desc_en", "zkn_desc_check"):
        continue
    try:
        _m = __import__(_stem)
        for _k in dir(_m):
            if _k.startswith("DESC_"):
                BATCHES.append(getattr(_m, _k))
    except Exception as _e:
        print("  WARNING: could not load %s (%s)" % (_f, _e))

WORK = r"E:\Projects\SRW Z\_work"
INDENT = " "        # the Japanese opens each paragraph with a fullwidth space

# EACH SET HAS ITS OWN BOX WIDTH, measured from the Japanese line lengths
# (max columns: KW 50, PT 34, RT 54). Using one number for all three wrapped
# character entries 47% too wide, and the renderer does NOT re-wrap - it draws
# the overflow on the following line, on top of the text already there.
WIDTH = {"KW": 48, "PT": 34, "RT": 52}


def cols(s):
    """Rendered columns. Characters in 0x2E-0x3D ( ./0-9:;<= ) are emitted as
    FULLWIDTH by the menu encoder (they are control codes as raw ASCII), so
    they occupy two columns each - count them that way or every line with a
    number or a full stop silently overflows."""
    return sum(2 if 0x2E <= ord(c) <= 0x3D else 1 for c in s)


def wrap(par, width):
    out, cur = [], INDENT
    for w in par.split():
        cand = (cur + " " + w) if cur.strip() else cur + w
        if cols(cand) <= width:
            cur = cand
        else:
            out.append(cur)
            cur = w
    if cur.strip():
        out.append(cur)
    return out


def render(text, key):
    lines = []
    for par in text.split("\n"):
        par = par.strip()
        if par:
            lines += wrap(par, WIDTH.get(key, 48))
    return "\n".join(lines)


def main():
    dry = "--dry" in sys.argv
    a = os.path.join(WORK, "analysis")
    jp = json.load(io.open(os.path.join(a, "zkn_jp.json"), encoding="utf-8"))
    p = os.path.join(a, "zkn_en.json")
    en = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    # Collect everything into one {key: {id: text}} map. Later sources win, so a
    # hand-written entry in zkn_desc_en.py overrides a batch translation.
    # A batch key may name the target field: "PT:DSC2" writes DSC2 instead of
    # DSCR. Plain "PT" means DSCR.
    todo = {}
    for batch in BATCHES:
        for key, ents in batch.items():
            for ri, t in ents.items():
                todo.setdefault(key, {})[str(ri)] = t
    for ri, t in KW_DSCR.items():
        todo.setdefault("KW", {})[str(ri)] = t

    n = n2 = 0
    bad = []
    for key, ents in todo.items():
        field = "DSCR"
        if ":" in key:
            key, field = key.split(":", 1)
        for ri, text in ents.items():
            try:
                text.encode("ascii")
            except UnicodeEncodeError as e:
                bad.append("%s/%s: non-ASCII %r" % (key, ri, text[e.start:e.end]))
                continue
            if ri not in jp.get(key, {}):
                bad.append("%s/%s: no such record" % (key, ri))
                continue
            body = render(text, key)
            d = en.setdefault(key, {}).setdefault(ri, {})
            d[field] = body
            n += 1
            j = jp[key][ri]
            # DSC2 is often the same text again; copy DSCR into it when the
            # Japanese matches ignoring line breaks, so it never shows Japanese
            # beside an English DSCR.
            if (field == "DSCR" and "DSC2" not in d
                    and j.get("DSC2", "").replace("\n", "")
                    == j.get("DSCR", "").replace("\n", "")):
                d["DSC2"] = body
                n2 += 1
    for b in bad:
        print("  REJECTED %s" % b)
    print("descriptions written: %d DSCR, %d DSC2 (identical in the Japanese)"
          % (n, n2))
    worst = {}
    for k, ents in todo.items():
        kk = k.split(":")[0]
        for t in ents.values():
            for l in render(t, kk).split("\n"):
                worst[kk] = max(worst.get(kk, 0), cols(l))
    print("widest wrapped line per set: %s   (limits %s)" % (worst, WIDTH))
    if dry:
        print("(dry run - nothing written)")
        return
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(en, ensure_ascii=False, indent=1))
    print("-> %s" % p)


if __name__ == "__main__":
    main()
