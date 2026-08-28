# -*- coding: utf-8 -*-
"""Regenerate analysis/srvc_en_by_hash.json, the published battle-line export.

compare_captions.py reads this file: it is how someone with only a japanese
disc can see our english beside it. The english is keyed by sha1 of the
japanese line, so the file carries our translation and not one character of
the original text - which is what makes it publishable at all.

It has to be REGENERATED whenever analysis/srvc_en.json changes. It was built
ad hoc the first time and had no generator, so nothing kept the two in step,
and a stale export shows a reader text the build no longer contains. That is
the same failure that put 148 regressed captions in 0.8.98: a copy of the
truth, made once, trusted afterwards.

    srvc_en.json  --(here)-->  srvc_en_by_hash.json  --> compare_captions.py

Run it after any caption edit, before committing.

Usage: export_captions.py [--check]
       --check  exit 1 if the published file is stale, write nothing
"""
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "analysis", "srvc_work.json")
EN = os.path.join(ROOT, "analysis", "srvc_en.json")
OUT = os.path.join(ROOT, "analysis", "srvc_en_by_hash.json")
NOTE = ("our english battle lines keyed by sha1 of the japanese line, so no "
        "index table and no japanese text is needed")


def build():
    work = json.load(io.open(WORK, encoding="utf-8"))
    en = json.load(io.open(EN, encoding="utf-8"))
    lines, missing = {}, 0
    for x in work:
        v = en.get(str(x["i"]))
        if not v:
            missing += 1
            continue
        lines[hashlib.sha1(x["jp"].encode("cp932", "ignore"))
              .hexdigest()[:16]] = v
    return lines, missing


def main():
    lines, missing = build()
    blob = json.dumps({"note": NOTE, "lines": lines},
                      ensure_ascii=False, indent=0)
    if "--check" in sys.argv:
        cur = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur == blob:
            print("export up to date: %d lines" % len(lines))
            return 0
        print("STALE: %s does not match analysis/srvc_en.json - "
              "run export_captions.py" % os.path.relpath(OUT, ROOT))
        return 1
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(blob)
    print("lines exported : %d" % len(lines))
    if missing:
        print("no translation : %d" % missing)
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
