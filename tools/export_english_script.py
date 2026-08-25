# -*- coding: utf-8 -*-
"""Export the ENGLISH script as standalone, publishable source.

The translation only ever existed inside the disc image. The image cannot be
published (it is the game), so without this the project is not forkable: the
public repo carries the toolchain but 0.0% of the 68,416 translated lines. If
the only copy of the image is lost, so is the translation.

This writes our English keyed by (record, offset) and NOTHING of the original:

  * no japanese source text - the pairs are what would make it a derivative
    dump of Banpresto's script
  * just the record index, the byte offset, the slot size, and our English

That is enough for anyone with their own dump of the game to re-apply the whole
translation with tools/apply_english_script.py, and it is our own work product
rather than the publisher's text.

Rows that still contain japanese are reported and SKIPPED, so the export cannot
quietly leak original prose.

Usage: export_english_script.py <iso> <out.json>
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

JP = re.compile(u"[぀-ゟ゠-ヿ一-鿿]")
LATIN = re.compile(r"[A-Za-z]")
# structural marks that are part of the engine's text, not japanese prose
ALLOWED = set(u"「」《》…・ー　")


def has_japanese(s):
    return any(JP.match(c) and c not in ALLOWED for c in s)


def main():
    iso, out = sys.argv[1], sys.argv[2]
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()

    rows, skipped = [], []
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        buf = bytes(data)
        i = 0
        while i < len(buf):
            j = buf.find(b"\x00", i)
            if j == -1:
                j = len(buf)
            seg = buf[i:j]
            if len(seg) > 2:
                try:
                    s = seg.decode("cp932")
                except Exception:
                    i = j + 1
                    continue
                if LATIN.search(s):
                    k = j
                    while k < len(buf) and buf[k] == 0:
                        k += 1
                    if has_japanese(s):
                        skipped.append((idx, i, s[:40]))
                    else:
                        rows.append({"rec": idx, "off": i, "slot": k - i, "en": s})
            i = j + 1

    io.open(out, "w", encoding="utf-8").write(
        json.dumps({"note": "English translation only. No original japanese text. "
                            "Keyed by record index and byte offset in DATA_STAGE.BIN.",
                    "rows": rows}, ensure_ascii=False, indent=0))
    print("exported %d english strings -> %s" % (len(rows), out))
    print("skipped %d rows that still contain japanese:" % len(skipped))
    for r in skipped[:10]:
        print("   rec%-4d off=%-7d %s" % r)
    # prove the export is clean
    t = io.open(out, encoding="utf-8").read()
    leak = sum(1 for c in t if JP.match(c) and c not in ALLOWED)
    print("japanese characters in the export: %d" % leak)


if __name__ == "__main__":
    main()
