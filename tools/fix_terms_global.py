# -*- coding: utf-8 -*-
"""Term fixes across ALL 205 STAGE records, not just the 26 that were exported.

tools/fix_terms_pass.py iterates analysis/review/rec*.json, so it only ever
touched rec109-150. 141 other records hold ~49,000 spoken lines that no rule
has ever reached - e.g. "Kashimaru" appears 85 times, all of them outside the
reviewed range.

Rules here are UNCONDITIONAL english->english, so every token must be
DISTINCTIVE enough that it cannot appear legitimately. Replacements must be the
same length or shorter; the tail of the slot is re-padded with NULs.

Matching runs on DECODED text, never on raw bytes. In cp932 the trail byte of
the opening quote mark is 0x75, which is ASCII 'u' - a word character - so a
byte-level \\b boundary never fires on a name that opens a line of speech. That
bug silently skipped every such row for every rule.

Usage: fix_terms_global.py <iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

# (wrong, right) - distinctive tokens only, shrink-or-equal
RULES = [
    ("Kashimaru", "Kashmir"),    # Kashmir Valle, King Gainer. 85 rows.
    ("Kashimar",  "Kashmir"),
    ("Norbu",     "Norb"),       # Eureka Seven. 50 rows outside the reviewed set.
    ("Norub",     "Norb"),
    ("Tziine",    "Ziene"),
    ("Tsine",     "Ziene"),
    ("Zaidel",    "Seidel"),
    ("Zaydel",    "Seidel"),
    ("Zeidel",    "Seidel"),
    ("Katsura",   "Kei"),       # 桂 = Kei Katsuragi; "Katsura" misreads the kanji
    ("Barre",     "Valle"),     # Kashmir Valle, per the King Gainer wiki
]

NUL = b"\x00"


def fix_record(data):
    """Return (new_bytes, hits). Length is preserved exactly, so every pointer
    into the record stays valid: each NUL-terminated string is rewritten in
    place and the slack re-padded with NULs."""
    buf = bytearray(data)
    hits = 0
    i, n = 0, len(buf)
    while i < n:
        j = buf.find(NUL, i)
        if j == -1:
            j = n
        seg = bytes(buf[i:j])
        if seg:
            try:
                txt = seg.decode("cp932")
            except Exception:
                txt = None
            if txt is not None:
                new_txt = txt
                found = 0
                for wrong, right in RULES:
                    new_txt, k = re.subn(r"\b%s\b" % wrong, right, new_txt)
                    found += k
                if found:
                    enc = new_txt.encode("cp932")
                    if len(enc) <= len(seg):
                        buf[i:j] = enc + NUL * (len(seg) - len(enc))
                        hits += found
        i = j + 1
    return bytes(buf), hits


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, per, total = {}, {}, 0
    for idx, (hdr, data) in enumerate(items):
        if data is None:
            continue
        new, hits = fix_record(data)
        if hits:
            edited[idx] = new
            per[idx] = hits
            total += hits

    print("replacements: %d across %d records" % (total, len(edited)))
    for idx in sorted(per)[:12]:
        print("   rec%-4d %d" % (idx, per[idx]))
    if len(per) > 12:
        print("   ... %d more records" % (len(per) - 12))
    if not write:
        print("\n(dry run - pass --write to apply)")
        f.close()
        return

    import multiprocessing
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close()
    pool.join()
    for idx, plain in edited.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written")


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


if __name__ == "__main__":
    main()
