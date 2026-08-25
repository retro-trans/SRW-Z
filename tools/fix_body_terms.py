# -*- coding: utf-8 -*-
"""Normalise names and terms INSIDE dialogue, not just on the speaker line.

apply_names.py fixed speaker lines game-wide, but a character's name also
appears in the prose - and there it was still drifting. Agents kept reporting
rows where the speaker line above already said "Lowen" while the line itself
said "Leben", or "Kei" over "Katsura".

Two kinds of fix, both conditioned on the JAPANESE so we never rename the wrong
thing:

1. NAME VARIANTS -> canonical, from analysis/names/map.json. Only applied to a
   row whose Japanese actually contains that character's katakana, and only for
   variants distinctive enough to be safe (>= 4 characters, not an English
   word). "Kei", "Ray", "Gain" and friends are never touched by substring
   replacement.

2. TERM FIXES, listed below with the Japanese that must be present:
   百鬼 -> "Hyakki", never "Mykene". Mykene (ミケーネ) is Great Mazinger's
    # ヴォダラ宮 is the PALACE (15 rows say "Vodara Palace", 4 wrongly say
    # "Vodarac"); ヴォダラク is the religious order. One agent tried to
    # "correct" the palace TO Vodarac, conflating the two.
    (u"ヴォダラ宮", "Vodarac", "Vodara"),
   empire; 百鬼帝国 is Getter Robo Go's. 8 rows had it wrong, and a proofreading
   agent then "unified" three correct rows TO the wrong one - so this is
   enforced centrally. ミケーネ appears 0 times in the corpus.
   スカブ -> "Scub", never "scab"/"scabs" - Scub Coral is a linked glossary
   term, so the prose was calling it "scabs" while the link said Scub Coral.

Usage: fix_body_terms.py <iso> [--dry-run]
"""
import io
import json
import multiprocessing
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, strings

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (japanese that must be present, wrong spelling, right spelling)
TERMS = [
    (u"\u767e\u9b3c", "Mykene", "Hyakki"),
    (u"\u30b9\u30ab\u30d6", "scabs", "Scubs"),
    (u"\u30b9\u30ab\u30d6", "scab", "Scub"),
]

# never substring-replace these: too short or real English words
UNSAFE = {"Kei", "Ray", "Rey", "Gain", "Boss", "Four", "Jun", "Mome", "Dove",
          "Hap", "Blume", "Chiru", "Maaie", "Eina", "Bask", "Jie", "T Bone"}


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    m = json.load(io.open(os.path.join(WORK, "analysis", "names", "map.json"),
                          encoding="utf-8"))
    groups = {g["jp"]: g for g in json.load(io.open(
        os.path.join(WORK, "analysis", "names", "groups.json"), encoding="utf-8"))}
    # jp katakana -> [(wrong, right)]
    subs = {}
    for e in m:
        jp, can = e["jp"], e["canonical"]
        if can in UNSAFE or len(can) < 4:
            continue
        for v in groups.get(jp, {}).get("variants", {}):
            if v == can or len(v) < 4 or v in UNSAFE:
                continue
            if not re.match(r"^[A-Za-z][A-Za-z .'-]*$", v):
                continue
            subs.setdefault(jp, []).append((v, can))

    jp_stage = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    edited, n_name, n_term = {}, 0, 0

    for idx, (hdr, dec) in enumerate(items):
        if dec is None or idx >= len(jp_stage) or jp_stage[idx][1] is None:
            continue
        jb, eb = bytes(jp_stage[idx][1]), bytearray(dec)
        jmap = {}
        for s, e in strings(jb):
            try:
                jmap[s] = jb[s:e].decode("cp932")
            except UnicodeDecodeError:
                pass
        touched = False
        for s, e in strings(bytes(eb)):
            try:
                t = bytes(eb[s:e]).decode("cp932")
            except UnicodeDecodeError:
                continue
            j = jmap.get(s, "")
            if not j:
                continue
            nt = t
            for jp_key, pairs in subs.items():
                if jp_key not in j:
                    continue
                for wrong, right in pairs:
                    if wrong in nt:
                        nt = re.sub(r"\b%s\b" % re.escape(wrong), right, nt)
            for jp_key, wrong, right in TERMS:
                if jp_key in j and wrong in nt:
                    nt = re.sub(r"\b%s\b" % re.escape(wrong), right, nt)
            if nt == t:
                continue
            nb = nt.encode("cp932")
            if len(nb) > len(t.encode("cp932")):
                continue      # only ever shrink; a longer line could overflow
            eb[s:s + len(nb)] = nb
            touched = True
            n_name += 1
        if touched:
            edited[idx] = bytes(eb)
    print("body-text rows normalised: %d across %d records" % (n_name, len(edited)))
    if dry or not edited:
        return
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close(); pool.join()
    for n, plain in edited.items():
        hdr = items[n][0]
        blob = packed[n]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % n
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert set(changed) <= set(items[n][0] for n in edited), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed" % len(changed))


if __name__ == "__main__":
    main()
