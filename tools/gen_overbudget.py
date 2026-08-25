# -*- coding: utf-8 -*-
"""Worklist for every scenario line still Japanese in the shipped build.

Most are NOT untranslated - they have English that exceeds the row's byte budget,
so apply_record skips them and the original Japanese bytes remain. The job is
therefore mostly TIGHTENING existing English, not translating from scratch.

Output: analysis/overbudget_jp.json
   [{rec, row, offset, budget, need, over, jp, en}]
"""
import glob
import importlib.util
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import apply_stage as A

out = []
no_en = []
for py in sorted(glob.glob(os.path.join(WORK, "tools", "rec*_en.py"))):
    n = int(os.path.basename(py)[3:6])
    js = os.path.join(WORK, "analysis", "rec%03d_script.json" % n)
    dec = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
    if not (os.path.exists(js) and os.path.exists(dec)):
        continue
    rows = json.load(io.open(js, encoding="utf-8"))
    orig = bytearray(open(dec, "rb").read())
    spec = importlib.util.spec_from_file_location("r%d" % n, py)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception:
        continue
    T = getattr(m, "T", {})
    for idx, r in enumerate(rows):
        # only real dialogue; skip bytecode the guard refuses anyway
        if not A.translatable(orig, r["offset"]):
            continue
        jp = r["text"]
        if not any(u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿" for c in jp):
            continue
        en = A._TIGHTEN.get("%d:%d" % (n, idx), T.get(idx))
        if en is None:
            # covered by a later offset-keyed pass?
            if any(off == r["offset"] for off, b, j in A._M2_BY_REC.get(n, [])):
                continue
            if any(off == r["offset"] for off, b, j in A._M3_BY_REC.get(n, [])):
                continue
            no_en.append({"rec": n, "row": idx, "offset": r["offset"],
                          "budget": r["budget"], "jp": jp})
            continue
        # emulate apply_record: prefix + encode, ellipsis-first trim
        lead = 0
        while (lead < 4 and r["offset"] + lead < len(orig)
               and orig[r["offset"] + lead] < 0x20
               and orig[r["offset"] + lead] != 0x0A):
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        is_dlg = ("\n" in en and len(first) <= 15
                  and not first.endswith((".", "!", "?")))
        cur = en
        enc = bytes(orig[r["offset"]:r["offset"] + lead]) + \
            A.pencode(cur, "ascii" if is_dlg else "menu")
        if len(enc) <= r["budget"]:
            continue                     # fits (trim ladder can handle ==)
        out.append({"rec": n, "row": idx, "offset": r["offset"],
                    "budget": r["budget"], "need": len(enc),
                    "over": len(enc) - r["budget"], "jp": jp, "en": en})

p = os.path.join(WORK, "analysis", "overbudget_jp.json")
with io.open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
p2 = os.path.join(WORK, "analysis", "untranslated_jp.json")
with io.open(p2, "w", encoding="utf-8") as f:
    json.dump(no_en, f, ensure_ascii=False, indent=1)

print("OVER BUDGET (English exists, too long): %d" % len(out))
print("NO ENGLISH AT ALL                     : %d" % len(no_en))
if out:
    import collections
    c = collections.Counter(x["over"] for x in out)
    print("\nbytes over budget:")
    for k in sorted(c)[:12]:
        print("   +%-3d bytes : %d rows" % (k, c[k]))
    print("\nworst offenders:")
    for x in sorted(out, key=lambda z: -z["over"])[:6]:
        print("   rec%03d row %-4d +%d (need %d, budget %d)"
              % (x["rec"], x["row"], x["over"], x["need"], x["budget"]))
        print("      %r" % x["en"][:70])
print("\nwritten -> %s\n           %s" % (p, p2))
