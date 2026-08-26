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

    # Verified 2026-08-25 against akurasu / series wikis and recorded in
    # analysis/glossary_sources.json, but never propagated to the script until
    # 2026-08-26 - the DB was corrected and the dialogue was not. All of these
    # are shrink-or-equal so they can be written in place; Kiel->Kihel and
    # Suesson->Sweatson GROW and are handled by fix_terms_grow.py instead.
    ("Olson",     "Orson"),     # akurasu: Orson D. Verne (Orguss)
    ("Runa",      "Luna"),      # akurasu: Luna Gusuku (Gravion)
    ("Gonjii",    "Gonzy"),     # Eureka Seven canonical
    ("Misha",     "Micha"),     # Eureka Seven canonical
    # NOT "Soreil" -> "Sorel". Checked the corpus: all 137 are Dianna SOREIL
    # (Turn A), which akurasu spells exactly that way. Only the Eureka Seven
    # character ドミニク・ソレル is "Dominic Sorel", and his full name is already
    # correct. A global rename here would have renamed the wrong queen.
    ("Tiptree",   "Tiptory"),
    ("Teraru",    "Teralu"),
    ("Reeven",    "Lowen"),     # 4th spelling of レーベン, found in COMPDATA
    ("Kiel",      "Kihel"),     # Kihel Heim (Turn A). GROWS by one byte, which
                                # the slot-aware write below absorbs.
]

NUL = b"\x00"


skipped_tight = [0]


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
                    # Use the whole SLOT (string + its NUL padding), not just
                    # the string, so a replacement one byte longer still fits
                    # where the row has slack. Record length is still preserved
                    # exactly - we never move the slot's end - so every offset
                    # in the record stays valid. Kiel->Kihel needed this: 346 of
                    # 347 rows had the spare byte already.
                    k = j
                    while k < n and buf[k] == 0:
                        k += 1
                    # STRICTLY less: the slot must keep at least one NUL as the
                    # string's terminator. Filling it exactly ran the row into
                    # the next string and merged two lines of dialogue into one
                    # ("...Aquarion...」??? 「So you fuse"). A row that cannot
                    # take the extra byte is left alone and reported, not
                    # squeezed.
                    if len(enc) < k - i:
                        buf[i:k] = enc + NUL * (k - i - len(enc))
                        hits += found
                    else:
                        skipped_tight[0] += 1
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
    if skipped_tight[0]:
        print("rows too tight for the longer name (left alone): %d"
              % skipped_tight[0])
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
