# -*- coding: utf-8 -*-
"""Scope DATA/NISVDATA.BIN - the intermission UI strings.

The intermission screen shows SRポイント / 資金 / 出撃 / 小隊 / 第N話, none of which
exist in the ELF. They live here, in a 7-record banlz container that no pass has
ever touched, which is why status.py (STAGE + COMPDATA + SRVC only) reported
"100%" while the screen was visibly Japanese.

Writes analysis/nisv_todo.json for translation.
"""
import io
import json
import os
import struct
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

SEC = 2048
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
boot = f.read(0x120000)
k = boot.find(b"\\\\DATA\\\\NISVDATA.BIN;1")
lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
f.seek(lba * SEC)
blob = bytearray(f.read(nsec * SEC))
f.close()
print("NISVDATA at LBA %d, %d sectors" % (lba, nsec))

recs = banlz.decompress_all(blob)
print("records: %d" % len(recs))

items = []
en_n = 0
for ri, (off, data) in enumerate(recs):
    if data is None:
        continue
    i = 0
    while i < len(data):
        j = data.find(b"\x00", i)
        if j < 0:
            break
        if 2 <= j - i <= 120:
            try:
                s = bytes(data[i:j]).decode("cp932")
            except UnicodeDecodeError:
                s = None
            if s:
                if real_text(s):
                    k2 = j
                    while k2 < len(data) and data[k2] == 0:
                        k2 += 1
                    items.append({"rec": ri, "offset": i,
                                  "budget": k2 - i - 1, "jp": s})
                elif all(0x20 <= ord(c) < 0x7F or 0xFF01 <= ord(c) <= 0xFF60
                         for c in s) and len(s) > 2:
                    en_n += 1
        i = j + 1

uniq = {}
for x in items:
    uniq.setdefault(x["jp"], 0)
    uniq[x["jp"]] += 1

print("Japanese strings : %d slots, %d unique" % (len(items), len(uniq)))
print("English strings  : %d" % en_n)
p = os.path.join(WORK, "analysis", "nisv_todo.json")
with io.open(p, "w", encoding="utf-8") as fh:
    json.dump(items, fh, ensure_ascii=False, indent=1)
print("written -> %s\n" % p)
for s, n in sorted(uniq.items(), key=lambda kv: -kv[1])[:36]:
    print("  x%-4d %s" % (n, s[:52].replace("\n", " / ")))
