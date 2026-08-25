# -*- coding: utf-8 -*-
"""Count REAL untranslated Japanese in the pilot DB and SRVC, not binary noise.

A naive "contains kana or kanji" test massively over-counts: COMPDATA and SRVC
are full of binary that decodes as valid Shift-JIS ('c逗', 'ｱ-逗', '揺>\\t').
That is the same false positive that let the _M2 pass write over scenario
bytecode, so filter properly BEFORE sending anything to a translator.

Real text must:
  - decode cleanly as cp932
  - contain no control bytes other than \\n
  - be >=60% Japanese//ASCII-printable characters
  - have >=2 Japanese characters
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

SEC = 2048


def jp_count(s):
    """Kana and kanji ONLY.

    Do NOT count the fullwidth ASCII block (U+FF01-FF60): our own SRVC encoder
    writes '．．．' for an ellipsis, so counting it flagged 11,170 lines of
    already-translated English ('Not bad, Gain Bijou．．．!') as untranslated
    Japanese - and would have sent them to be re-translated.
    """
    return sum(1 for c in s
               if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")


def real_text(s):
    if not s:
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 and c != "\n":
            return False
        if 0xFF61 <= o <= 0xFF9F:        # halfwidth katakana = decoded noise
            return False
    nj = jp_count(s)
    if nj < 2:
        return False
    good = sum(1 for c in s
               if jp_count(c) or 0x20 <= ord(c) < 0x7F
               or 0xFF01 <= ord(c) <= 0xFF60 or c in u"　、。「」・ー…")
    return good / float(len(s)) >= 0.6


def walk(d, lo, hi, minlen=4):
    i = lo
    while i < hi:
        j = d.find(b"\x00", i)
        if j < 0 or j >= hi:
            break
        if j - i >= minlen:
            try:
                yield i, bytes(d[i:j]).decode("cp932")
            except UnicodeDecodeError:
                pass
        i = j + 1


def main():
    iso = os.path.join(WORK, "iso", "srwz_fix3.bin")
    f = open(iso, "rb")
    f.seek(1823000 * SEC)
    cd, _ = banlz.decompress_record(bytearray(f.read(74 * SEC)), 0)
    f.seek(1313214 * SEC)
    srvc = bytearray(f.read(3313040))
    f.close()

    for label, data, lo, hi, out_name in (
            ("PILOT/DB", cd, 0, 0x66380, "db_todo.json"),
            ("SRVC", srvc, 0, len(srvc), "srvc_todo.json")):
        raw = noise = real = 0
        items = []
        for off, s in walk(data, lo, hi):
            if jp_count(s) < 2:
                continue
            raw += 1
            if not real_text(s):
                noise += 1
                continue
            real += 1
            k = data.find(b"\x00", off)
            e = k
            while e < len(data) and data[e] == 0:
                e += 1
            items.append({"offset": off, "budget": e - off - 1,
                          "used": k - off, "jp": s})
        print("%s:" % label)
        print("   looks Japanese (naive) : %d" % raw)
        print("   binary noise rejected  : %d" % noise)
        print("   REAL text to translate : %d  (%d chars)"
              % (real, sum(len(x["jp"]) for x in items)))
        p = os.path.join(WORK, "analysis", out_name)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=1)
        print("   -> %s" % p)
        for x in items[:8]:
            print("      0x%06X bud %-4d %s"
                  % (x["offset"], x["budget"], x["jp"][:44].replace("\n", " / ")))
        print()


if __name__ == "__main__":
    main()
