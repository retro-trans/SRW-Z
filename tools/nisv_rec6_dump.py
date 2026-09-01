# -*- coding: utf-8 -*-
"""Dump the rec6 help book as translatable paragraphs.

Writes analysis/help_jp.json, which is GITIGNORED (*_jp.json) - it holds the
original japanese and must never be committed. The english lives in
analysis/help_en.json keyed by sha1 of the japanese, so the committed side
carries no japanese prose.

Usage: nisv_rec6_dump.py <iso> [--out FILE]
"""
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import nisv_rec6
import nisv_rec6_para as para

LBA, SECT = 1568269, 272
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def key(text):
    return hashlib.sha1(text.encode("cp932", "ignore")).hexdigest()[:16]


def load_rec6(iso):
    f = open(iso, "rb")
    f.seek(LBA * 2048)
    items = banlz.decompress_all(f.read(SECT * 2048))
    f.close()
    return bytes(items[6][1])


def main():
    iso = sys.argv[1]
    out = ROOT + "/analysis/help_jp.json"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]

    b = load_rec6(iso)
    secs, _ = nisv_rec6.parse(b)
    rows = []
    for s in secs:
        if s.runs is None:
            continue
        for n, p in enumerate(para.group(s.runs)):
            rows.append({
                "key": key(p.text),
                "sec": s.index,
                "n": n,
                "kind": p.kind,
                "attr": p.attr,
                "x": p.first_x,
                "cx": p.cont_x,
                "y": p.y,
                "jp": p.text,
                "chars": len(para.strip(p.text)),
            })
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    uniq = len(set(r["key"] for r in rows))
    print("%d paragraphs (%d unique) from %d sections -> %s"
          % (len(rows), uniq, len(set(r["sec"] for r in rows)), out))
    print("%d japanese characters" % sum(r["chars"] for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
