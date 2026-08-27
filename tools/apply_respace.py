# -*- coding: utf-8 -*-
"""Write the model-number re-spacing fixes into the pool IN PLACE.

gen_weapons.translate() joined model numbers with a NON-OVERLAPPING pair regex,
so "ＭＭＩ－ＧＡＵ２５Ａ" came out as "MM I-GA U25A" - 77 names shredded. The
joiner is fixed; this applies the result.

Only entries whose characters are IDENTICAL and whose SPACING differs are
touched, so nothing is retranslated and no naming decision is made here. All of
them get shorter, so each is written into its existing slot - no repack, which
would disturb the pointers repaired in 0.8.90.

Text is encoded with the MENU encoding: '.' and the digits are control codes in
the 0x13A290 reader and must be fullwidth.

Usage: apply_respace.py <iso> <fixes.json> [--write]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
import banlz
import pool
from patch import encode

SEC, LBA, NSEC = 2048, 1823000, 74
NUL = b"\x00"


def load(iso):
    f = open(iso, "rb"); f.seek(LBA * SEC); raw = f.read(NSEC * SEC); f.close()
    return bytes(banlz.decompress_all(raw)[0][1])


def main():
    iso, src = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    rec = load(iso)
    cur = pool.entries(rec)
    review = json.load(open("analysis/weapon_review.json", encoding="utf-8"))
    byoff = {("%#x" % r["off"]): r["idx"] for r in review}
    fixes = json.load(open(src, encoding="utf-8"))

    buf = bytearray(rec)
    done = skipped = 0
    for k, text in sorted(fixes.items()):
        idx = byoff.get(k)
        if idx is None:
            skipped += 1
            continue
        off, old, slot = cur[idx]
        nb = encode(text, "menu")
        if len(nb) >= slot:
            print("   SKIP %-30r needs %d, slot %d" % (text[:28], len(nb), slot))
            skipped += 1
            continue
        if bytes(buf[off:off + len(old)]) != old:
            print("   SKIP %#x: content moved" % off)
            skipped += 1
            continue
        buf[off:off + slot] = nb + NUL * (slot - len(nb))
        done += 1
    print("re-spaced: %d, skipped: %d" % (done, skipped))

    # nothing may have moved: same entry count, same starts
    after = pool.entries(bytes(buf))
    assert len(after) == len(cur), "entry count changed"
    assert [a for a, _, _ in after] == [a for a, _, _ in cur], "a string start moved"
    print("entry starts unchanged: %d entries" % len(after))
    if not write or not done:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return
    blob = banlz.compress_record(bytes(buf))
    if len(blob) > NSEC * SEC:
        blob = banlz.compress_record_optimal(bytes(buf))
    if len(blob) > NSEC * SEC:
        raise SystemExit("REFUSED: %d > slot %d" % (len(blob), NSEC * SEC))
    out = bytearray(NSEC * SEC)
    out[:len(blob)] = blob
    f = open(iso, "r+b"); f.seek(LBA * SEC); f.write(bytes(out)); f.close()
    assert load(iso) == bytes(buf), "readback mismatch"
    print("written and verified (%d compressed bytes)" % len(blob))


if __name__ == "__main__":
    main()
