# -*- coding: utf-8 -*-
"""Export JP/EN pairs for proofreading, straight from the SHIPPED image.

Why not tools/recNNN_en.py: those modules hold PRE-transform text (ASCII
quotes, no glossary links, pre-wrap). What the player sees has kagi quotes,
《links》 and the final wrapping, and several passes have edited it in place
since. Proofreading has to see the shipped string.

Mapping a script row to its shipped string: rows carry their Japanese offset.
Most rows sit at the same offset in our build; rows healed by option-3
relocation moved, and the pointer that referenced them was rewritten. So for a
row at JP offset O, find a 4-aligned word equal to BASE+O in the JAPANESE
record, read the word at that same position in OURS, and that value is where
the row lives now.

Output: analysis/review/recNNN.json - [{row, off, slot, jp, en}]

Usage: export_review.py <rec> [<rec> ...]
"""
import json
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(WORK, "analysis", "review")


def main():
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(os.path.join(WORK, "iso", "srwz_cap.bin"), "rb")
    f.seek(LBA * SECTOR)
    en = banlz.decompress_all(f.read(SIZE))
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for a in sys.argv[1:]:
        n = int(a)
        rows = json.load(io.open(os.path.join(WORK, "analysis",
                                              "rec%03d_script.json" % n),
                                 encoding="utf-8"))
        jb, eb = bytes(jp[n][1]), bytes(en[n][1])
        # every 4-aligned pointer in the JP record, by target offset
        ptr = {}
        for i in range(0, len(jb) - 4, 4):
            v = struct.unpack_from("<I", jb, i)[0] - BASE
            if 0 <= v < len(jb):
                ptr.setdefault(v, []).append(i)
        out, moved, missing = [], 0, 0
        for idx, r in enumerate(rows):
            off = r.get("offset")
            jtext = r.get("text") or ""
            if off is None or not jtext:
                continue
            cur = off
            if not (off < len(eb) and eb[off:off + 1] not in (b"", b"\x00")):
                cur = None
            for p in ptr.get(off, []):
                if p + 4 <= len(eb):
                    v = struct.unpack_from("<I", eb, p)[0] - BASE
                    if 0 <= v < len(eb):
                        if v != off:
                            moved += 1
                        cur = v
                        break
            if cur is None:
                missing += 1
                continue
            e = cur
            while e < len(eb) and eb[e] != 0:
                e += 1
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            try:
                etext = eb[cur:e].decode("cp932")
            except UnicodeDecodeError:
                missing += 1
                continue
            out.append({"row": idx, "off": cur, "slot": k - cur,
                        "jp": jtext, "en": etext})
        p = os.path.join(OUT, "rec%03d.json" % n)
        json.dump(out, io.open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
        print("rec %-4d %5d rows exported (%d relocated, %d unmapped) -> %s"
              % (n, len(out), moved, missing, os.path.basename(p)))


if __name__ == "__main__":
    main()
