# -*- coding: utf-8 -*-
"""Write translated help text back into NISVDATA.BIN.

Reads analysis/nisv_en.json - {japanese: english} - and rewrites every field
whose japanese matches, in place, NUL padded. A field's start never moves, so
nothing that indexes into these records can be disturbed.

REFUSES, never truncates:
  * a translation that does not fit its field's room
  * anything that will not encode as cp932

Both are reported with the offending string so the text can be shortened
deliberately rather than silently cut. Japanese is two bytes per character and
english roughly one, so a translation is normally about half the size; a
refusal means the english genuinely ran long.

The touched records are recompressed and must fit their existing slots, the
same discipline STAGE uses. Idempotent: a field already holding its
translation is skipped.

Usage: nisv_apply.py <iso> [--write]
"""
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from nisv_extract import strings, LBA, SECTORS, PROSE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "nisv_en.json")


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    # KEYED BY sha1(japanese)[:16], NOT by the japanese itself. This project
    # refuses to redistribute the original script - check_publishable.py
    # enforces it - and a japanese-keyed table would have carried 235 lines
    # of it into the repo. mtvpros_en.py was converted to hashes for the
    # same reason. The japanese never has to be stored: it is read from the
    # disc the user already owns and hashed on the spot.
    en = json.load(io.open(SRC, encoding="utf-8"))

    def key(t):
        return hashlib.sha1(t.encode("cp932", "ignore")).hexdigest()[:16]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * 2048)
    raw = bytearray(f.read(SECTORS * 2048))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, _ in items)

    edited, done, skip, miss = {}, 0, [], 0
    for ri in PROSE:
        b = bytearray(items[ri][1])
        hit = False
        for off, t, ln, room in list(strings(bytes(b))):
            new = en.get(key(t))
            if not new:
                miss += 1
                continue
            try:
                nb = new.encode("cp932")
            except UnicodeEncodeError as e:
                skip.append((t, new, "not cp932: %s" % e))
                continue
            if nb == bytes(b[off:off + len(nb)]) and b[off + len(nb)] == 0:
                continue                      # already applied
            if len(nb) >= room:
                skip.append((t, new, "needs %d bytes, field holds %d"
                             % (len(nb) + 1, room)))
                continue
            b[off:off + room] = nb + bytes(room - len(nb))
            done += 1
            hit = True
        if hit:
            edited[ri] = bytes(b)
    print("%d field(s) translated, %d refused, %d still japanese"
          % (done, len(skip), miss))
    for t, new, why in skip[:20]:
        print("   REFUSED %s" % why)
        print("      jp %r" % t[:60])
        print("      en %r" % new[:60])
    if not write or not edited:
        if not write:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0

    for ri, plain in edited.items():
        hdr = items[ri][0]
        nxt = min([h for h in heads if h > hdr] or [SECTORS * 2048])
        blob = banlz.compress_record(plain)
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(plain)
        if len(blob) > nxt - hdr:
            raise SystemExit("rec%d grew past its slot (%d > %d)"
                             % (ri, len(blob), nxt - hdr))
        raw[hdr:hdr + len(blob)] = blob
        for k in range(hdr + len(blob), nxt):
            raw[k] = 0
        print("   rec%d %d bytes (slot %d)" % (ri, len(blob), nxt - hdr))
    check = banlz.decompress_all(bytes(raw))
    assert len(check) == len(items), "record count changed"
    f.seek(LBA * 2048)
    f.write(bytes(raw))
    f.close()
    print("NISVDATA.BIN rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
