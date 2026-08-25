# -*- coding: utf-8 -*-
"""Build an OFFSET-KEYED worklist of dialogue the extractor never saw.

464 fields (416 speaker-quote + 48 scene-header) are absent from every
recNNN_script.json because strdump.dump() rejected them:
  - `kana >= 1`      : all-kanji lines ('花江\\n「勝平！！」', '～駿河湾　漁港～')
  - strict shift_jis : NEC extensions (ビアルⅠ世, ガンダムＭｋ－Ⅱ)
  - `jp_score >= .60`: scene headers are mostly U+3000 padding

DO NOT fix this by re-running strdump into script.json. Every recNNN_en.py T dict
is keyed by ROW INDEX, so inserting rows renumbers everything after them and
silently invalidates translations across 167 files - the same failure shape as
the v1.32 mass revert. This emits an offset-keyed list instead, applied by the
_M3 pass in apply_stage (offset-keyed, immune to renumbering).

Output: analysis/missing3_jp.json  {rec: [[offset, budget, jp], ...]}
budget = nbytes + trailing NUL padding, matching scriptdump's convention.
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

KAKKO = u"「"
WAVE, WAVE2 = u"～", u"〜"


def main():
    stage = bytearray(open(os.path.join(WORK, "extracted", "DATA_STAGE.BIN"),
                           "rb").read())
    recs = banlz.decompress_all(stage)
    work = sorted(int(x) for x in
                  open(os.path.join(WORK, "analysis", "recs_all.txt")).read().split())

    out = {}
    n_q = n_h = 0
    for n in work:
        js = os.path.join(WORK, "analysis", "rec%03d_script.json" % n)
        if not os.path.exists(js):
            continue
        known = set(r["offset"] for r in json.load(io.open(js, encoding="utf-8")))
        data = recs[n][1]
        rows = []
        i = 0
        while i < len(data):
            j = data.find(b"\x00", i)
            if j < 0:
                break
            if j > i and i not in known:
                raw = bytes(data[i:j])
                try:
                    s = raw.decode("cp932")
                except UnicodeDecodeError:
                    s = None
                if s:
                    is_q = ("\n" in s and KAKKO in s and len(s) >= 4)
                    is_h = ((WAVE in s or WAVE2 in s) and len(s) >= 6)
                    if is_q or is_h:
                        pad = 0
                        q = j
                        while q < len(data) and data[q] == 0:
                            pad += 1
                            q += 1
                        rows.append([i, len(raw) + pad, s])
                        if is_q:
                            n_q += 1
                        else:
                            n_h += 1
            i = j + 1
        if rows:
            out[str(n)] = rows

    p = os.path.join(WORK, "analysis", "missing3_jp.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    tot = sum(len(v) for v in out.values())
    uniq = set()
    for v in out.values():
        for _, _, s in v:
            uniq.add(s)
    print("records: %d" % len(out))
    print("fields : %d  (%d quote, %d header)" % (tot, n_q, n_h))
    print("UNIQUE strings to translate: %d" % len(uniq))
    print("written -> %s" % p)

    tight = [(o, b, s) for v in out.values() for o, b, s in v
             if b < len(s.encode("cp932")) + 4]
    print("\nslots with <4 bytes of headroom: %d" % len(tight))


if __name__ == "__main__":
    main()
