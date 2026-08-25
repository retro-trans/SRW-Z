# -*- coding: utf-8 -*-
"""Find T entries whose 'English' is actually the Japanese source copied through.

Discovered 2026-08-17: rec109 rows 652-655 apply cleanly, fit budget, report
no errors - and ship Japanese, because the translation stored in T IS the source
text. Nothing in the pipeline ever asserted that a T value is English, so these
are invisible to every existing check (budget audits, over-count, the bytecode
guard).

Writes analysis/passthrough_jp.json for retranslation.
"""
import glob
import importlib.util
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def jp_chars(s):
    return sum(1 for c in s
               if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")


def main():
    out = []
    per_rec = {}
    for py in sorted(glob.glob(os.path.join(WORK, "tools", "rec*_en.py"))):
        n = int(os.path.basename(py)[3:6])
        js = os.path.join(WORK, "analysis", "rec%03d_script.json" % n)
        if not os.path.exists(js):
            continue
        rows = json.load(io.open(js, encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("p%d" % n, py)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        except Exception:
            continue
        for idx, en in getattr(m, "T", {}).items():
            if idx >= len(rows):
                continue
            nj = jp_chars(en)
            if nj == 0:
                continue
            # Japanese in the value: passthrough, or a stray untranslated word
            jp = rows[idx]["text"]
            same = en.replace(u"…", "..") == jp.replace(u"…", "..")
            out.append({"rec": n, "row": idx, "offset": rows[idx]["offset"],
                        "budget": rows[idx]["budget"], "jp": jp, "en": en,
                        "jp_chars": nj, "identical": same})
            per_rec[n] = per_rec.get(n, 0) + 1

    p = os.path.join(WORK, "analysis", "passthrough_jp.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    ident = sum(1 for x in out if x["identical"])
    print("T entries containing Japanese: %d" % len(out))
    print("  identical to the source (pure passthrough): %d" % ident)
    print("  partly Japanese (stray words)             : %d" % (len(out) - ident))
    print("\nrecords affected: %d" % len(per_rec))
    for n, c in sorted(per_rec.items(), key=lambda x: -x[1])[:15]:
        print("   rec%03d : %d" % (n, c))
    print("\nexamples:")
    for x in out[:8]:
        print("   rec%03d row %-5d %s" % (x["rec"], x["row"],
                                          "IDENTICAL" if x["identical"] else "partial"))
        print("      %r" % x["en"][:60])
    print("\nwritten -> %s" % p)


if __name__ == "__main__":
    main()
