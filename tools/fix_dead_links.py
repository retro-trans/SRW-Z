# -*- coding: utf-8 -*-
"""Make every glossary link in dialogue resolve to a real keyword entry.

A link is 《term》 in the dialogue text, and the game looks the term up in the
keyword bank (DATA_MTVZKNKW, 52 entries). 24 distinct terms - 34 occurrences -
did not match any entry: plurals the table stores in the singular ("PLANTs" vs
"PLANT"), variants ("Siberia Railway" vs "Siberian Railway", "Evidence 01" vs
"Evidence ０１"), stray punctuation inside the markers ("(Patrick Zala)"), and
terms with no entry at all ("Orfan", "Balmar War", "Kaneda Ikuo", "Ghingnham").

A dead link is not cosmetic: the user hit an emulator CRASH opening the UN
terminal scene, whose record carries five dead links alongside the good ones.

Three fixes, none of which lengthens a string:
  1. plural outside the markers   《PLANTs》   -> 《PLANT》s
  2. punctuation outside          《(Patrick Zala)》 -> (《Patrick Zala》)
  3. no entry at all              《Orfan》    -> Orfan          (unwrapped)

Usage: fix_dead_links.py <iso> [--dry-run]
"""
import multiprocessing
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
import zkn
from rewrap_dialogue import LBA, SECTOR, SIZE, strings

KW_LBA, KW_SIZE = 1823200, 32768
OPEN, CLOSE = "《", "》"

# term as linked -> the exact keyword it should point at (same or fewer bytes)
ALIAS = {
    "Siberia Railway": "Siberian Railway",
    "Evidence Zero-One": "Evidence ０１",
    "Evidence 01": "Evidence ０１",
    "Side 3": "Side ３",
    "LOGOS": "Logos",
    "Morgenroete": "Morgenroete Inc．",
    "PLANT Council Chairman": "PLANT Supreme Council Chairman",
    "Orb Defense": "Battle of Orb",
}


def keywords(iso_path):
    f = open(iso_path, "rb")
    f.seek(KW_LBA * SECTOR)
    out = set()
    for off, d in banlz.decompress_all(f.read(KW_SIZE)):
        if d is None:
            continue
        try:
            magic, kind, ver, chunks = zkn.parse(zkn.payload_of(bytes(d)))
        except Exception:
            continue
        if magic != "ZKAN":
            continue
        w = next((c[2] for c in chunks if c[0] == "WORD"), b"")
        try:
            out.add(w.split(b"\x00")[0].decode("cp932"))
        except Exception:
            pass
    return out


def fix_text(t, kw, stats):
    def repl(m):
        term = m.group(1)
        if term in kw:
            return m.group(0)
        # 1. plural / possessive outside the link
        for suf in ("s", "'s", "es"):
            if term.endswith(suf) and term[:-len(suf)] in kw:
                stats["plural"] += 1
                return OPEN + term[:-len(suf)] + CLOSE + suf
        # 2. punctuation outside the link
        stripped = term.strip("()<>『』【】 ")
        if stripped != term and stripped in kw:
            stats["punct"] += 1
            lead = term[:len(term) - len(term.lstrip("()<>『』【】 "))]
            tail = term[len(term.rstrip("()<>『』【】 ")):]
            return lead + OPEN + stripped + CLOSE + tail
        # 3. a known variant of a real entry
        if term in ALIAS and ALIAS[term] in kw:
            new = ALIAS[term]
            if len(new.encode("cp932")) <= len(term.encode("cp932")):
                stats["alias"] += 1
                return OPEN + new + CLOSE
        # 4. no entry - drop the markers, keep the words
        stats["unwrapped"] += 1
        return term
    return re.sub(OPEN + "(.*?)" + CLOSE, repl, t)


def fix_record(rec, kw, stats):
    d = bytearray(rec)
    n = 0
    for s, e in strings(bytes(rec)):
        chunk = bytes(d[s:e])
        if b"\x81\x73" not in chunk:
            continue
        try:
            t = chunk.decode("cp932")
        except UnicodeDecodeError:
            continue
        nt = fix_text(t, kw, stats)
        if nt == t:
            continue
        nb = nt.encode("cp932")
        k = e
        while k < len(d) and d[k] == 0:
            k += 1
        slot = k - s
        if len(nb) >= slot:
            continue
        d[s:s + slot] = nb + b"\x00" * (slot - len(nb))
        n += 1
    return (bytes(d), n) if n else (None, 0)


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    kw = keywords(iso_path)
    print("keyword entries: %d" % len(kw))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    stats = {"plural": 0, "punct": 0, "alias": 0, "unwrapped": 0}

    edited = {}
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        new, n = fix_record(bytes(dec), kw, stats)
        if new is not None:
            edited[idx] = (hdr, new)
    print("records to rebuild: %d | %s" % (len(edited), stats))
    if dry or not edited:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    packed = dict(pool.map(_compress, [(i, d) for i, (h, d) in edited.items()]))
    pool.close(); pool.join()

    for idx, (hdr, plain) in edited.items():
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "record %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sum(1 for o in before if check[o] != before[o])
    assert changed == len(edited), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % changed)


if __name__ == "__main__":
    main()
