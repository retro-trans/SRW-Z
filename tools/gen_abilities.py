# -*- coding: utf-8 -*-
"""Worklist for the ability/skill DESCRIPTION block in COMPDATA.

0x6B8F0..0x6D0C0 - prose describing unit abilities ('気力１３０以上で発動可能。…').
No pass has ever touched it. Sits between the weapon names (which end at
0x6B8F0) and the unit display-name list (which starts at 0x6D0C0), which is why
earlier region labels kept mis-attributing it.

Output: analysis/abilities_work.json  [{offset, budget, used, jp}]
"""
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

LO, HI = 0x6B8F0, 0x6D0C0


def is_jp(s):
    return any(u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿" for c in s)


def main():
    iso = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "iso", "srwz_fix3.bin")
    f = open(iso, "rb")
    f.seek(1823000 * 2048)
    cd, _ = banlz.decompress_record(bytearray(f.read(74 * 2048)), 0)
    f.close()

    out = []
    i = LO
    while i < HI:
        j = cd.find(b"\x00", i)
        if j < 0 or j >= HI:
            break
        if j - i >= 2:
            try:
                s = bytes(cd[i:j]).decode("cp932")
            except UnicodeDecodeError:
                s = None
            if s and is_jp(s):
                k = j
                while k < len(cd) and cd[k] == 0:
                    k += 1
                out.append({"offset": i, "used": j - i, "budget": k - i - 1, "jp": s})
        i = j + 1

    p = os.path.join(WORK, "analysis", "abilities_work.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("ability descriptions: %d" % len(out))
    print("total JP chars      : %d" % sum(len(x["jp"]) for x in out))
    print("written -> %s\n" % p)
    for x in out:
        print("0x%05X bud %-4d %s" % (x["offset"], x["budget"],
                                      x["jp"].replace("\n", " / ")))


if __name__ == "__main__":
    main()
