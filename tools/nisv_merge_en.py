# -*- coding: utf-8 -*-
"""Merge the per-record NISVDATA translations into one store for nisv_apply.py.

KEYED BY sha1(japanese)[:16], NEVER by the japanese itself. This project
refuses to redistribute the original script and check_publishable.py enforces
it, so a japanese-keyed table would have carried 235 lines of the original into
the repo - which is exactly what the first version of these tables did, and
exactly why mtvpros_en.py was converted to hashes before it. The japanese never
has to be stored: nisv_apply.py reads it from the disc the user already owns
and hashes it on the spot.

Sources, each a list of [hash, english]:

    analysis/nisv_rec5_en.json    90 - the SR Point, formation and save tutorial
    analysis/nisv_rec6_toc.json     145 - the Strategy Q&A index
    analysis/nisv_rec6_blurbs.json   17 - the chapter blurbs
    analysis/nisv_rec6_xref.json     49 - the "see also" term lines,
                                          rendered from nisv_terms.py

Add a new file here as more of rec6 is translated.

Usage: nisv_merge_en.py
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = ["nisv_rec5_en.json", "nisv_rec6_toc.json",
         "nisv_rec6_blurbs.json", "nisv_rec6_xref.json"]
OUT = os.path.join(ROOT, "analysis", "nisv_en.json")


def main():
    out = {}
    for name in PARTS:
        p = os.path.join(ROOT, "analysis", name)
        if not os.path.exists(p):
            print("missing %s - skipped" % name)
            continue
        rows = json.load(io.open(p, encoding="utf-8"))
        for k, v in rows:
            if k in out and out[k] != v:
                raise SystemExit("%s disagrees with an earlier file on %s"
                                 % (name, k))
            out[k] = v
        print("%-26s %3d row(s)" % (name, len(rows)))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print("%d translation(s) -> %s" % (len(out), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
