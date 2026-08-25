# -*- coding: utf-8 -*-
"""Measure untranslated Japanese in the boot ELF (SLPS_258.87).

status.py never looked at the ELF, so the "100%" figures excluded every menu and
HUD string. The intermission screen still shows SRポイント / 資金 / 第N話 / 出撃 /
小隊, so there is real work here.

Reads the ELF straight out of the ISO at LBA 455.
"""
import os
import re
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = 2048
ELF_LBA, ELF_LEN = 455, 3471624
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "iso",
                                                         "srwz_fix3.bin")


def jp(s):
    return sum(1 for c in s if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")


def real_text(s):
    if jp(s) < 1:
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 and c != "\n":
            return False
        if 0xFF61 <= o <= 0xFF9F:
            return False
    good = sum(1 for c in s
               if jp(c) or 0x20 <= ord(c) < 0x7F
               or 0xFF01 <= ord(c) <= 0xFF60 or c in u"　、。「」・ー…％")
    return good / float(max(len(s), 1)) >= 0.6


f = open(ISO, "rb")
f.seek(ELF_LBA * SEC)
d = f.read(ELF_LEN)
f.close()

items = []
i = 0
while i < len(d):
    j = d.find(b"\x00", i)
    if j < 0:
        break
    if 2 <= j - i <= 200:
        try:
            s = d[i:j].decode("cp932")
        except UnicodeDecodeError:
            s = None
        if s and real_text(s):
            k = j
            while k < len(d) and d[k] == 0:
                k += 1
            items.append({"offset": i, "budget": k - i - 1,
                          "used": j - i, "jp": s})
    i = j + 1

print("ELF strings still containing Japanese: %d" % len(items))
print("total JP characters: %d" % sum(jp(x["jp"]) for x in items))

import collections
c = collections.Counter(x["jp"] for x in items)
print("\nmost frequent:")
for s, n in c.most_common(30):
    print("   x%-3d bud? %-4s %s" % (n, "", s[:46].replace("\n", " / ")))

import io
import json
p = os.path.join(WORK, "analysis", "elf_todo.json")
with io.open(p, "w", encoding="utf-8") as fh:
    json.dump(items, fh, ensure_ascii=False, indent=1)
print("\nwritten -> %s" % p)
