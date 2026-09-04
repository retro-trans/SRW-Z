# -*- coding: utf-8 -*-
u"""Shinn Asuka is "Shinn" (シン), and Bask Om is "Bask Om" (バスク・オム).

42 dialogue/synopsis rows spelled シン as "Shin" (one n) against 1,872 correct
"Shinn"; two rows spelled バスク・オム "Basque Om" against one "Bask Om". Both
verified against the japanese - only rows whose paired JP actually contains シン
get the Shin -> Shinn change, so an unrelated "Shin" is never touched.

Shin -> Shinn grows a row by one byte each, so a row with no spare is reported
and left rather than truncated. Bask is same-region same-op.

Usage: fix_shinn.py <iso> [--write]
"""
import os
import re
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
SHIN = u"シン".encode("cp932")
WB = re.compile(rb"\bShin\b")


def _compress(job):
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(data)
    return ri, blob


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def pm(eb, jb):
    out = {}
    for p in range(0, min(len(eb), len(jb)) - 4, 4):
        ve = struct.unpack_from("<I", eb, p)[0] - BASE
        vj = struct.unpack_from("<I", jb, p)[0] - BASE
        if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in out:
            out[ve] = vj
    return out


def slot_at(b, off):
    z = b.find(b"\x00", off)
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    jp = [(h, bytes(d)) for h, d in banlz.decompress_all(load("iso/srwz.bin"))
          if isinstance(h, int) and d is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    touched, nshin, nbask, skipped = {}, 0, 0, []
    for ri in range(min(len(live), len(jp))):
        eb = live[ri][1]
        if b"Shin" not in eb and b"Basque Om" not in eb:
            continue
        jb = jp[ri][1]
        m = pm(bytes(eb), jb)
        changed = False
        for eo, jo in sorted(m.items()):
            et, slot = slot_at(eb, eo)
            jt, _ = slot_at(jb, jo)
            if not et or not jt:
                continue
            new = et
            if b"Basque Om" in new:
                new = new.replace(b"Basque Om", b"Bask Om")
            if WB.search(new) and SHIN in jt:
                new = WB.sub(b"Shinn", new)
            if new == et:
                continue
            if len(new) > slot:
                skipped.append((ri, eo, et))
                continue
            eb[eo:eo + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
            nshin += len(WB.findall(et)) if (SHIN in jt and WB.search(et)) else 0
            nbask += 1 if b"Basque Om" in et else 0
            changed = True
        if changed:
            touched[ri] = eb

    print("Shin -> Shinn: %d ; Basque Om -> Bask Om: %d ; records touched: %d"
          % (nshin, nbask, len(touched)))
    print("rows skipped (no spare byte): %d" % len(skipped))
    for ri, eo, et in skipped[:8]:
        print("   rec%-3d @%#06x: %s" % (ri, eo, et.decode("cp932", "replace").replace("\n", " / ")[:56]))
    if not touched or not write:
        if touched:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return 0

    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, bytes(touched[ri])))
    got = {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2)) as ex:
        for ri, blob in ex.map(_compress, [(r, n - h, dd) for r, h, n, dd in jobs]):
            got[ri] = blob
    for ri, hdr, nxt, dd in jobs:
        blob = got[ri]
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written (%d records)" % len(touched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
