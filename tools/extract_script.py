# -*- coding: utf-8 -*-
"""Extract every text string from a disc image into an editable JSON file.

This is the front door for anyone starting their own translation. It reads the
image YOU dumped from YOUR OWN copy of the game, so the original Japanese never
has to be redistributed - you extract it yourself, from your own disc.

Two ways in:

  * a virgin japanese image  -> you get the Japanese script to translate from,
    and you are starting a new language
  * a patched image from this project -> you get the current English, and you
    are fixing or revising an existing translation

Either way the output is the same shape, and tools/apply_script.py writes it
back. Round-trip is exact: extract, change nothing, apply, and the image is
byte-identical.

Output rows carry what an editor needs and what the writer needs:

    {"rec": 109, "off": 45312, "slot": 96, "cols": [4, 31, 28],
     "text": "Kouji\\n\\u300cSomething he says.\\u300d"}

  rec/off  where it lives; do not change these
  slot     bytes available - your replacement must fit (see docs/TECHNICAL.md
           for what to do when it does not)
  cols     display width of each line, placeholders already expanded
  text     the string itself; the FIRST line is the speaker and is structural

Usage:
  extract_script.py <iso> <out.json>              everything
  extract_script.py <iso> <out.json> --dialogue   only spoken dialogue
  extract_script.py <iso> <out.json> --rec 109    one record
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

KAGI = u"「"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}
PRINTABLE = re.compile(r"[A-Za-z0-9]")
JP = re.compile(u"[぀-ゟ゠-ヿ一-鿿]")


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def looks_like_text(s):
    """Reject binary that happens to decode. Real text is either dialogue or
    mostly printable."""
    if not s or len(s) < 2:
        return False
    if KAGI in s:
        return True
    if JP.search(s):
        return sum(1 for c in s if JP.match(c) or 0x20 <= ord(c) < 0x7F) >= 0.8 * len(s)
    ok = sum(1 for c in s if 0x20 <= ord(c) < 0x7F or c == "\n")
    return ok >= 0.85 * len(s) and PRINTABLE.search(s)


def main():
    iso, out = sys.argv[1], sys.argv[2]
    only_dlg = "--dialogue" in sys.argv
    only_rec = None
    if "--rec" in sys.argv:
        only_rec = int(sys.argv[sys.argv.index("--rec") + 1])

    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()

    rows, jp_rows, en_rows = [], 0, 0
    for idx, (hdr, data) in enumerate(items):
        if data is None or (only_rec is not None and idx != only_rec):
            continue
        buf = bytes(data)
        i = 0
        while i < len(buf):
            j = buf.find(b"\x00", i)
            if j == -1:
                j = len(buf)
            seg = buf[i:j]
            if len(seg) > 1:
                try:
                    s = seg.decode("cp932")
                except Exception:
                    i = j + 1
                    continue
                # Reject anything that does not re-encode to the EXACT bytes
                # it came from. cp932 has duplicate mappings (the NEC/IBM
                # extension rows), so some byte pairs decode to a character
                # that re-encodes differently - and binary data that happens
                # to contain printable ASCII decodes to nonsense. Either way
                # the row would be silently rewritten on apply, so it is not
                # extractable text. This makes round-trip exact by construction.
                try:
                    stable = s.encode("cp932") == seg
                except Exception:
                    stable = False
                if stable and looks_like_text(s) and not (only_dlg and KAGI not in s):
                    k = j
                    while k < len(buf) and buf[k] == 0:
                        k += 1
                    rows.append({"rec": idx, "off": i, "slot": k - i,
                                 "cols": [ecols(l) for l in s.split("\n")],
                                 "text": s})
                    if JP.search(s):
                        jp_rows += 1
                    else:
                        en_rows += 1
            i = j + 1

    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"note": "Extracted from your own disc image. rec/off/slot are "
                 "structural - do not change them. Edit 'text' only.",
         "source": os.path.basename(iso),
         "rows": rows}, ensure_ascii=False, indent=0))
    print("extracted %d strings -> %s" % (len(rows), out))
    print("  containing japanese : %d" % jp_rows)
    print("  latin only          : %d" % en_rows)
    if jp_rows > en_rows:
        print("\nThis looks like an untranslated image: translate the 'text' "
              "fields and apply with tools/apply_script.py")
    else:
        print("\nThis looks like a translated image: edit the 'text' fields "
              "and apply with tools/apply_script.py")


if __name__ == "__main__":
    main()
