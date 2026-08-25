# -*- coding: utf-8 -*-
"""Normalise speaker names game-wide to the wiki-canonical spelling.

112 Japanese speakers ship under more than one English spelling - 1,310 lines on
a non-dominant variant. Proofreading agents cannot fix this: the brief locks the
speaker line, and an agent reading one 80-row slice cannot know that "Raven"
appeared as "Leben" three records earlier.

The canonical form comes from analysis/names/map.json, built against akurasu's
SRW Z Pilot Database. The wiki BEATS our majority - 桂 ships as "Katsura" 157
times against "Kei" 114, and the canonical is Kei Katsuragi, so majority-vote
would have picked the wrong name.

EXCLUDED deliberately (see SKIP): a Japanese string that maps to two different
characters cannot be renamed by script, and a canonical form that came from
inference rather than a source is not canonical at all.

Applies to EVERY record, not just the DeepSeek ones - the inconsistency is
game-wide. Rows that no longer fit are relocated (append + repoint + zero).

Usage: apply_names.py <iso> [--dry-run]
"""
import io
import json
import multiprocessing
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, strings

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# jp -> why it is not safe to rename by script
SKIP = {
    u"\u30ec\u30a4": "collision: both Ray Beams (Eureka Seven) and Rey Za "
                     "Barrel (SEED Destiny) are レイ, and every record mixes "
                     "both casts - needs per-line context",
    u"\u30b7\u30e5\u30e9\u30f3": "'Schlan' was inferred from the Chimera "
                                 "German-wordplay pattern, not cited; no source "
                                 "means keep the shipping 'Shuran'",
    u"\u30e1\u30fc\u30c6\u30eb": "rationale did not check out; unverified",
}


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    m = {e["jp"]: e["canonical"] for e in
         json.load(io.open(os.path.join(WORK, "analysis", "names", "map.json"),
                           encoding="utf-8"))}
    for k in SKIP:
        m.pop(k, None)
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, n_fix, n_reloc = {}, 0, 0
    per = {}
    for idx, (hdr, dec) in enumerate(items):
        if dec is None or idx >= len(jp) or jp[idx][1] is None:
            continue
        jb, eb = bytes(jp[idx][1]), bytearray(dec)
        jmap = {}
        for s, e in strings(jb):
            try:
                t = jb[s:e].decode("cp932")
            except UnicodeDecodeError:
                continue
            if "\n" in t:
                jmap[s] = t.split("\n")[0].strip()
        touched = False
        for off in sorted(jmap, reverse=True):
            want = m.get(jmap[off])
            if not want:
                continue
            # find the row in OUR record: same offset, or wherever it relocated
            cur = off
            nb4 = struct.pack("<I", BASE + off)
            for i in range(0, len(jb) - 4, 4):
                if jb[i:i + 4] == nb4 and i + 4 <= len(eb):
                    v = struct.unpack_from("<I", bytes(eb), i)[0] - BASE
                    if 0 <= v < len(eb):
                        cur = v
                    break
            e2 = cur
            while e2 < len(eb) and eb[e2] != 0:
                e2 += 1
            k = e2
            while k < len(eb) and eb[k] == 0:
                k += 1
            try:
                t = bytes(eb[cur:e2]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if "\n" not in t:
                continue
            parts = t.split("\n")
            if parts[0].strip() == want or not parts[0].strip():
                continue
            if len(parts[0]) > 20 or parts[0].lstrip().startswith((u"\u300c", '"')):
                continue                      # not a speaker line
            parts[0] = want
            nb = u"\n".join(parts).encode("cp932")
            if len(nb) < k - cur:
                eb[cur:k] = nb + b"\x00" * (k - cur - len(nb))
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op, npp = struct.pack("<I", BASE + cur), struct.pack("<I", BASE + new_off)
                cnt, j = 0, 0
                while True:
                    j = eb.find(op, j)
                    if j < 0:
                        break
                    if j % 4 == 0:
                        eb[j:j + 4] = npp
                        cnt += 1
                        j += 4
                    else:
                        j += 1
                if cnt < 1:
                    del eb[new_off:]
                    continue
                for x in range(cur, k):
                    eb[x] = 0
                n_reloc += 1
            n_fix += 1
            per[jmap[off]] = per.get(jmap[off], 0) + 1
            touched = True
        if touched:
            edited[idx] = bytes(eb)
    print("speaker lines renamed: %d (relocated %d) across %d records"
          % (n_fix, n_reloc, len(edited)))
    print("skipped by design: %s" % ", ".join(SKIP))
    for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:12]:
        print("   %-12s %d lines -> %s" % (k, v, m[k]))
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
