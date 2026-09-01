# -*- coding: utf-8 -*-
"""Reassemble rec6's help text into paragraphs, ready to translate.

WHAT THE EARLIER TOOLS GOT WRONG. nisv_extract.py says "every field is a
self-contained title or one-line sentence". That holds for the table of
contents and the chapter blurbs - and is FALSE for the answer bodies, which is
where the remaining ~2,800 strings live. A body paragraph is split across many
fields at fixed character counts, and the splits fall MID-WORD:

    フォーメーション                     <- a term, drawn highlighted
    とは、２機または３機で構成された小      <- ends inside 小隊
    隊が選択可能な、並び方を変える事で戦闘能力が変化する
    新システムです。

A field is one RENDERED LINE, not a unit of meaning. Translating them one at a
time would produce nonsense, which is the whole reason this exists.

THREE KINDS OF FIELD, and only one is prose:

  prose   the fragments above, joined in order to rebuild the paragraph
  term    a field naming a glossary entry, drawn highlighted and referenced
          inline by the sentence around it. Checked against nisv_terms.TERMS
          rather than guessed from length - guessing called a 1-character
          marker a "term" and split every paragraph into single fields.
  marker  a few bytes of link plumbing between them. Never text. The prose is
          entirely FULL-width, so a field of half-width kana is plumbing that
          merely decodes as kana.

Paragraph boundaries are the markers.

BUDGET. Japanese is two bytes per character and english about one, so the same
paragraph needs roughly half the room; the english is re-wrapped across the
SAME fields using each field's own room as that line's width.

Usage: nisv_paragraphs.py <iso> [--from OFF] [--n N]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from nisv_extract import LBA, SECTORS
from nisv_terms import TERMS

JP = re.compile(u"[぀-ヿ一-龥]")
CTRL = re.compile(u"[\x00-\x1f]")
HALFKANA = re.compile(u"^[｡-ﾟ\x20-\x7e]+$")


def kind(t):
    if t is None or not t:
        return "marker"
    if CTRL.search(t) or HALFKANA.match(t):
        return "marker"
    if t in TERMS:
        return "term"
    if not JP.search(t):
        return "marker"
    return "prose"


def fields(b):
    i = 0
    while i < len(b):
        z = b.find(b"\x00", i)
        if z < 0:
            break
        if z > i:
            k = z
            while k < len(b) and b[k] == 0:
                k += 1
            raw = b[i:z]
            try:
                t = raw.decode("cp932")
            except UnicodeDecodeError:
                t = None
            yield i, t, z - i, k - i
            i = k
        else:
            i = z + 1


def paragraphs(b, start=0):
    para = []
    for off, t, ln, room in fields(b):
        if off < start:
            continue
        k = kind(t)
        if k == "marker":
            if para:
                yield para
                para = []
            continue
        para.append((off, t, k, ln, room))
    if para:
        yield para


def main():
    iso = sys.argv[1]
    start = (int(sys.argv[sys.argv.index("--from") + 1], 0)
             if "--from" in sys.argv else 0x002e07)
    want = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3
    f = open(iso, "rb")
    f.seek(LBA * 2048)
    recs = banlz.decompress_all(f.read(SECTORS * 2048))
    f.close()
    b = bytes(recs[6][1])

    shown = 0
    for para in paragraphs(b, start):
        if all(k != "prose" for _o, _t, k, _l, _r in para):
            continue
        shown += 1
        room = sum(r for _o, _t, _k, _l, r in para)
        print("paragraph at %#08x - %d field(s), %d bytes of room"
              % (para[0][0], len(para), room))
        for off, t, k, ln, r in para:
            print("   %#08x %-5s %3d/%-3d %s" % (off, k, ln, r - 1, t))
        joined = "".join(t if k == "prose" else u"【" + t + u"】"
                         for _o, t, k, _l, _r in para)
        print("   REASSEMBLED: %s" % joined)
        print("   english budget: about %d characters\n" % room)
        if shown >= want:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
