# -*- coding: utf-8 -*-
"""Fill the pilot SHORT-name field, which the battle panel draws.

Each COMPDATA pilot record (stride 0xB0) carries TWO name fields:

    +0x00  u16 id
    +0x02  short name  <- the BATTLE PANEL draws this one
    +0x2E  full name   <- an earlier pass translated only this

So enemy pilots still showed Japanese in battle (チラム兵 under the enemy
unit) while their entry elsewhere read "Chiram Soldier". 262 of 933 records
were left Japanese in the short field; 256 of them already have an English
full name, which is copied down verbatim.

The short field runs from +0x02 to +0x2E, i.e. 44 bytes, and the longest
English name in play is 18 - no budget problem. Written with the safe splice
pattern: decompress from the CURRENT iso, edit, recompress, verify every
other record is byte-identical, then write back in place.

Usage: patch_pilot_shortnames.py <iso> [--dry-run]
"""
import re
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

import banlz

LBA, SECTOR, SIZE = 1823000, 2048, 151552
START, STRIDE, COUNT = 0x2160, 0xB0, 933
SHORT, FULL = 0x02, 0x2E
JP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")

# The full-name field is NOT trustworthy on its own. Surveying all 262 records
# turned up names that are plain wrong (\u30c7\u30e5\u30e9\u30f3\u30c0\u30eb -> "Rau", a different
# character entirely), first-names-only, blanks, and one with a stray kana
# ("\u30c6Titans"). Copying those down would promote each error into the battle
# panel, where it is far more visible than in the pilot list - so correct them
# here and write the fix to BOTH fields.
FIXES = {
    "\u30c7\u30e5\u30e9\u30f3\u30c0\u30eb": "Durandal",      # was "Rau" - wrong character
    "\u30b8\u30d6\u30ea\u30fc\u30eb": "Djibril",         # was "Lord"
    "\u30df\u30c9\u30ac\u30eb\u30c9": "Midgard",         # was "Meme"
    "\u30d6\u30e9\u30c3\u30c9\u30de\u30f3": "Bloodman",      # was "Fix"
    "\u30c0\u30b3\u30b9\u30bf": "DaCosta",           # was "Martin"
    "\u30de\u30fc\u30c9\u30c3\u30af": "Murdoch",         # was "Kojirou"
    "\u30b3\u30fc\u30d7\u30e9\u30f3\u30c9": "Copeland",      # was "Joseph" (first name only)
    "\u30ad\u30b5\u30ab": "Kisaka",              # was "Ledonir" (first name only)
    "\u30b7\u30ed\u30c3\u30b3": "Scirocco",          # was "Paptimus" (first name only)
    "\u30c6\u30a3\u30bf\u30fc\u30f3\u30ba": "Titans",        # one record read "\u30c6Titans"
    "\u30c8\u30c0\u30ab": "Todaka",              # was blank
    "\u30b5\u30c8\u30fc": "Sato",                # was blank
    "\u30d0\u30d0": "Baba",                  # was blank
    "\u30e1\u30c0\u30a4\u30e6": "Medaille",          # was blank
    "\u4e0d\u52d5": "Gen",                   # was fullwidth \uff27\uff25\uff2e
}


def field(rec, off, at):
    end = rec.index(b"\x00", off + at)
    try:
        return rec[off + at:end].decode("cp932")
    except UnicodeDecodeError:
        return None


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    iso = open(iso_path, "r+b")
    iso.seek(LBA * SECTOR)
    raw = iso.read(SIZE)
    items = banlz.decompress_all(raw)
    before = {o: bytes(d) for o, d in items if d is not None}

    hdr, dec = next((o, bytes(d)) for o, d in items if d is not None)
    rec = bytearray(dec)
    done = skipped = 0
    for k in range(COUNT):
        off = START + k * STRIDE
        short, full = field(rec, off, SHORT), field(rec, off, FULL)
        if not short or not JP.search(short):
            continue
        fixed = FIXES.get(short)
        if fixed:
            full = fixed
            enc_full = fixed.encode("cp932")
            room_full = STRIDE - FULL          # rest of the record
            end = rec.index(b"\x00", off + FULL)
            rec[off + FULL:end] = b"\x00" * (end - (off + FULL))
            rec[off + FULL:off + FULL + len(enc_full)] = enc_full
        elif not full or JP.search(full):
            skipped += 1                      # no English to copy down
            continue
        enc = full.encode("cp932")
        room = FULL - SHORT                   # 44 bytes
        assert len(enc) < room, "%r does not fit the short field" % full
        rec[off + SHORT:off + FULL] = enc + b"\x00" * (room - len(enc))
        done += 1
    print("short names filled: %d (left alone, no English full name: %d)"
          % (done, skipped))
    if dry or not done:
        return

    blob = banlz.compress_record_optimal(bytes(rec))
    k = len(raw)
    end = k
    while end > 0 and raw[end - 1] == 0:
        end -= 1
    slot = SIZE
    assert len(blob) <= slot, "record grew past its slot"
    new = bytearray(raw)
    new[hdr:hdr + len(blob)] = blob
    for i in range(hdr + len(blob), SIZE):
        new[i] = 0
    check = banlz.decompress_all(bytes(new))
    got = {o: bytes(d) for o, d in check if d is not None}
    assert set(got) == set(before), "record set changed"
    for o in before:
        if o == hdr:
            assert got[o] == bytes(rec), "edited record did not round-trip"
        else:
            assert got[o] == before[o], "record %#x changed" % o
    iso.seek(LBA * SECTOR)
    iso.write(bytes(new))
    iso.close()
    print("COMPDATA spliced in place; every other record byte-identical")


if __name__ == "__main__":
    main()
