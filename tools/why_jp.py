# -*- coding: utf-8 -*-
"""Given Japanese text seen in-game, find it and explain WHY it is still Japanese.

Written 2026-08-17 after answering the same question by hand three times from
screenshots. Checks every reason a string can survive untranslated, in order:

  1. not extracted at all - no row in recNNN_script.json. Then report WHICH
     strdump predicate rejected it (the `kana >= 1` rule and the strict
     shift_jis decode are the two known offenders, worth 350 and 66 fields).
  2. extracted but never translated - no entry in T / _M2 / _MISSING / _OBJ.
  3. translated but OVER budget - apply_record skips it and the JP bytes stay.
  4. refused by apply_stage.translatable() - the bytecode guard.
  5. not in STAGE at all - look in COMPDATA (names, episode titles, UI).

Usage:  python tools/why_jp.py ビアル
        python tools/why_jp.py 目覚めの日 --all
"""
import glob
import importlib.util
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz
import strdump

MIN_LEN, MIN_JP, MIN_CHARS = 4, 0.60, 2


def strdump_verdict(raw, s):
    why = []
    if len(raw) < MIN_LEN:
        why.append("raw < %d bytes" % MIN_LEN)
    try:
        raw.decode("shift_jis")
    except UnicodeDecodeError:
        why.append("strict shift_jis DECODE FAILS (NEC ext: use cp932)")
    if len(s) < MIN_CHARS:
        why.append("< %d chars" % MIN_CHARS)
    if strdump.has_halfwidth_noise(s):
        why.append("halfwidth noise")
    if sum(1 for ch in s if u"぀" <= ch <= u"ヿ") < 1:
        why.append("NO KANA (strdump requires kana >= 1)")
    if strdump.jp_score(s) < MIN_JP:
        why.append("jp_score %.2f < %.2f" % (strdump.jp_score(s), MIN_JP))
    return why


def field_at(data, k):
    s = data.rfind(b"\x00", 0, k) + 1
    e = data.find(b"\x00", k)
    if e < 0:
        e = len(data)
    return s, e


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    if not args:
        sys.exit(__doc__)
    needle = args[0].encode("cp932")

    import apply_stage as A

    stage = bytearray(open(os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read())
    recs = banlz.decompress_all(stage)
    work = set()
    p = os.path.join(WORK, "analysis", "recs_all.txt")
    if os.path.exists(p):
        work = set(int(x) for x in open(p).read().split())

    found = 0
    for n, (roff, data) in enumerate(recs):
        k = data.find(needle)
        while k >= 0:
            fs, fe = field_at(data, k)
            raw = bytes(data[fs:fe])
            try:
                s = raw.decode("cp932")
            except UnicodeDecodeError:
                s = "<undecodable>"
            found += 1
            print("=" * 72)
            print("rec%03d @0x%05X  %r" % (n, fs, s[:70]))
            print("   in work set: %s" % (n in work))

            js = os.path.join(WORK, "analysis", "rec%03d_script.json" % n)
            row_i = None
            if os.path.exists(js):
                rows = json.load(io.open(js, encoding="utf-8"))
                for i, r in enumerate(rows):
                    if r["offset"] == fs:
                        row_i = i
                        break
                if row_i is None:
                    print("   NOT EXTRACTED - no row at this offset")
                    v = strdump_verdict(raw, s)
                    print("   strdump rejected it: %s"
                          % ("; ".join(v) if v else "unclear - passes all predicates"))
                else:
                    r = rows[row_i]
                    print("   row %d, budget %d" % (row_i, r["budget"]))
                    py = os.path.join(WORK, "tools", "rec%03d_en.py" % n)
                    en = None
                    if os.path.exists(py):
                        spec = importlib.util.spec_from_file_location("r%d" % n, py)
                        m = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(m)
                        en = getattr(m, "T", {}).get(row_i)
                    if en is None:
                        m2 = {o: jp for o, b, jp in A._M2_BY_REC.get(n, [])}
                        if fs in m2:
                            print("   in _M2 -> %r" % A._M2.get(m2[fs]))
                        else:
                            print("   NOT TRANSLATED (absent from T and _M2)")
                    else:
                        nb = len(en.encode("cp932", "replace"))
                        print("   T = %r  (%d bytes)" % (en, nb))
                        if nb >= r["budget"]:
                            print("   OVER BUDGET %d >= %d -> skipped, stays Japanese"
                                  % (nb, r["budget"]))
                        else:
                            print("   fits - should be English in-game")
                    dec = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
                    if os.path.exists(dec):
                        o = bytearray(open(dec, "rb").read())
                        if not A.translatable(o, fs):
                            print("   REFUSED by translatable() - treated as bytecode")
            else:
                print("   no script.json for this record")
            if not show_all and found >= 6:
                print("\n(more hits suppressed; pass --all)")
                return
            k = data.find(needle, k + 1)

    if not found:
        print("not found in STAGE - checking COMPDATA")
        base, _ = banlz.decompress_record(
            bytearray(open(os.path.join(WORK, "extracted", "DATA_COMPDATA.BN"),
                           "rb").read()), 0)
        k = base.find(needle)
        while k >= 0:
            fs, fe = field_at(base, k)
            q = fe
            while q < len(base) and base[q] == 0:
                q += 1
            print("  COMPDATA @0x%05X %r  used %d, slot %d"
                  % (fs, bytes(base[fs:fe]).decode("cp932", "replace"),
                     fe - fs, q - fs))
            k = base.find(needle, k + 1)


if __name__ == "__main__":
    main()
