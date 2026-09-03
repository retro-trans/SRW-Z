# -*- coding: utf-8 -*-
u"""Move every STAGE string stranded past its record's japanese end back inside.

THE DEFECT (0.9.34, confirmed by single-variable test): a string placed at or
past the ORIGINAL JAPANESE record length does not exist to the game. Short ones
draw an empty box, long ones crash. Earlier passes relocated any line that
outgrew its slot to the record's tail, starting exactly at the old end, so the
FIRST relocated string in a record sits right on the boundary. 0.9.34 moved six
of them back by hand and fixed the stage 29 crash and the tutorial blank box.
It left 7,900 more, and rec160's ten just crashed the Overman scene after
Cynthia's 「Me too, King...」.

THE FIX is the same operation, done generally. Our english is shorter than the
japanese it replaced, so every record has NUL slack after its strings - bytes
that in the japanese held TEXT, so they are provably not bytecode. First-fit
each stranded string into that slack, repoint every word that pointed at it,
zero its old tail bytes, and when nothing is left past the boundary, cut the
record back to its japanese length so it is the shape the game expects.

Only slack AFTER a pointer-target string is used. The trailing padding the
japanese carries before its end is NOT used: zeros there might be a field the
game reads as zero, and the slack inside the pool is more than enough.

Header words 0x0c / 0x28 / 0x2c are never repointed - they hold BASE+length and
coincide with the first stranded string's address in every record.

INVARIANT, checked before anything is written: every non-header word that
resolved to a string in the original record resolves to BYTE-IDENTICAL text in
the new one. Strings are moved, never changed.

Strings with no gap big enough are REPORTED and left where they are; those need
a byte or two trimmed, which is editing, not relocation.

Usage: fix_stranded_strings.py <iso> [--write] [--only REC]
"""
import collections
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
JP_ISO = "iso/srwz.bin"
HDR_WORDS = {0x0c, 0x28, 0x2c}


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


def text_at(b, o):
    z = b.find(b"\x00", o)
    return bytes(b[o:z]) if z > o else None


def slot_end(b, o):
    """index of the first non-NUL after the string's terminator."""
    z = b.find(b"\x00", o)
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return e


def is_text(t):
    """Dialogue never carries control bytes and always decodes as cp932."""
    if t is None or len(t) < 2:
        return False
    if any(c < 0x20 and c != 0x0A for c in t):
        return False
    try:
        t.decode("cp932")
    except UnicodeDecodeError:
        return False
    return True


def pointer_map(b):
    """target offset -> [word offsets], genuine pointers only.

    Two coincidences have to be filtered out, and the invariant caught both:

    * A TARGET that is not text. A ".」\\0" line ending forms a value that
      resolves inside the record, and in rec0 twenty-four such "words" all
      landed on the same FF FF FF FF bytecode. Writing a string into the
      "slack" after that would corrupt the scenario. Targets must pass
      is_text().
    * A WORD that is itself text. That same ".」\\0" IS the word. Repointing
      it would rewrite a line ending; zeroing the moved string it lived in
      made it stop resolving, which is how this surfaced. A pointer word
      never sits inside a string span, so any that does is dropped.
    """
    cand = collections.defaultdict(list)
    for p in range(0, len(b) - 4, 4):
        if p in HDR_WORDS:
            continue
        v = struct.unpack_from("<I", b, p)[0] - BASE
        if 0 <= v < len(b) and is_text(text_at(b, v)):
            cand[v].append(p)
    mask = bytearray(len(b))
    for v in cand:
        n = len(text_at(b, v)) + 1                 # text plus its terminator
        mask[v:v + n] = b"\x01" * n
    out = {}
    for v, ws in cand.items():
        keep = [p for p in ws if not any(mask[p:p + 4])]
        if keep:
            out[v] = keep
    return out


def fix_record(eb, jb):
    """Returns (new_bytes, moved, unplaced) or None if nothing is stranded."""
    JPEND = len(jb)
    if len(eb) <= JPEND:
        return None
    d = bytearray(eb)
    pm = pointer_map(bytes(d))

    # A word can point INTO a string - at its second line, say - and that
    # target has the same terminator and the same slack as its parent. Treat
    # those as riders on the parent: they move with it, by the same delta, and
    # they contribute no gap of their own. Without this the same slack is
    # listed twice, two strings get placed in it, and the second wipes the
    # first - which is exactly what the invariant below caught the first time.
    tops = []
    riders = collections.defaultdict(list)        # parent -> [mid-string targets]
    for v in sorted(pm):
        if tops and v <= tops[-1] + len(text_at(d, tops[-1])):
            riders[tops[-1]].append(v)
        else:
            tops.append(v)

    stranded = sorted((v for v in tops if v >= JPEND), key=lambda v: -len(text_at(d, v)))
    if not stranded:
        return None

    # free ranges: slack after every top-level string INSIDE the bounds, merged
    raw_gaps = []
    for v in tops:
        if v >= JPEND:
            continue
        t = text_at(d, v)
        a = v + len(t) + 1                 # first byte after the terminator
        e = min(slot_end(d, v), JPEND)     # never spill past the boundary
        if e - a >= 2:                     # room for at least a 1-byte string + NUL
            raw_gaps.append([a, e])
    raw_gaps.sort()
    gaps = []
    for g in raw_gaps:
        if gaps and g[0] <= gaps[-1][1]:
            gaps[-1][1] = max(gaps[-1][1], g[1])
        else:
            gaps.append(g)
    gaps.sort(key=lambda g: -(g[1] - g[0]))

    # snapshot of what every word resolves to, for the invariant
    before = {w: text_at(d, v) for v, ws in pm.items() for w in ws}

    # Largest string first into the SMALLEST gap that takes it (best-fit).
    # Taking the largest gap instead shredded every big gap into pieces too
    # small for the 47-byte strings that came later: 78 unplaced against 41
    # the capacity said were unavoidable.
    gaps.sort(key=lambda g: g[1] - g[0])

    moved, unplaced = [], []
    for v in stranded:
        t = text_at(d, v)
        need = len(t) + 1
        for g in gaps:
            if g[1] - g[0] >= need:
                dst = g[0]
                delta = dst - v
                d[dst:dst + need] = t + b"\x00"
                words = list(pm[v])
                for r in riders.get(v, []):
                    words += pm[r]
                for w in words:
                    old = struct.unpack_from("<I", d, w)[0]
                    struct.pack_into("<I", d, w, old + delta)
                d[v:v + need] = b"\x00" * need          # clear the old tail bytes
                g[0] += need
                moved.append((v, dst, len(t), len(words)))
                break
        else:
            unplaced.append((v, len(t)))
        gaps.sort(key=lambda g: g[1] - g[0])

    # invariant: every original word still resolves to the same text
    for w, t in before.items():
        nv = struct.unpack_from("<I", d, w)[0] - BASE
        assert text_at(d, nv) == t, "word %#x no longer resolves to its text" % w

    # Whatever is still in the tail is either ORPHAN text - an earlier pass
    # re-relocated a string and never zeroed the copy it left behind - or a
    # string whose pointer the strict map does not see. Tell them apart by
    # looking for ANY aligned word in the record that lands inside the run:
    # referenced -> report and keep the tail; unreferenced -> it is dead
    # bytes, clear them. Only a tail that is provably clear gets cut.
    leftovers = []
    p = JPEND
    while p < len(d):
        if d[p] == 0:
            p += 1
            continue
        q = d.find(b"\x00", p)
        q = len(d) if q < 0 else q
        refs = []
        for w in range(0, len(d) - 4, 4):
            if w in HDR_WORDS:
                continue
            tv = struct.unpack_from("<I", d, w)[0] - BASE
            if p <= tv < q:
                refs.append(w)
        if refs:
            leftovers.append((p, q - p, refs))
            if not any(u[0] == p for u in unplaced):     # not already counted
                unplaced.append((p, q - p))
        else:
            d[p:q] = b"\x00" * (q - p)
        p = q
    if not unplaced and not any(d[JPEND:]):
        d = d[:JPEND]
    return bytes(d), moved, unplaced, leftovers


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None

    jp = [(h, bytes(x)) for h, x in banlz.decompress_all(load(JP_ISO))
          if isinstance(h, int) and x is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytes(x)) for h, x in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and x is not None]
    heads = sorted(h for h, _ in live)

    touched, tot_moved, tot_unplaced = {}, 0, []
    for ri in range(min(len(live), len(jp))):
        if only is not None and ri != only:
            continue
        res = fix_record(live[ri][1], jp[ri][1])
        if res is None:
            continue
        nb, moved, unplaced, leftovers = res
        touched[ri] = nb
        tot_moved += len(moved)
        for v, n in unplaced:
            tot_unplaced.append((ri, v, n, text_at(live[ri][1], v)))
        for p, n, refs in leftovers:
            print("  rec%-4d LEFTOVER @%#06x %3d bytes, referenced by %s : %r"
                  % (ri, p, n, [hex(w) for w in refs[:4]], live[ri][1][p:p + min(n, 50)]))
        tail = "" if not unplaced else "   %d UNPLACED" % len(unplaced)
        print("  rec%-4d %3d moved back inside, %#x -> %#x bytes%s"
              % (ri, len(moved), len(live[ri][1]), len(nb), tail))
        if only is not None:
            for v, dst, n, k in moved:
                print("        %#06x -> %#06x  %3d bytes  %d pointer word(s)  %s"
                      % (v, dst, n, k, text_at(live[ri][1], v).decode("cp932", "replace")
                         .replace("\n", " / ")[:60]))

    print("\nrecords touched : %d" % len(touched))
    print("strings moved   : %d" % tot_moved)
    print("strings UNPLACED: %d  (no gap big enough - need trimming)" % len(tot_unplaced))
    for ri, v, n, t in tot_unplaced:
        print("   rec%-4d @%#06x %3d bytes  %s" % (ri, v, n,
              (t or b"").decode("cp932", "replace").replace("\n", " / ")[:70]))

    if not touched or not write:
        if touched:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return 0

    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, touched[ri]))
    got = {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 1)) as ex:
        for ri, blob in ex.map(_compress, [(r, n - h, d) for r, h, n, d in jobs]):
            got[ri] = blob
    for ri, hdr, nxt, d in jobs:
        blob = got[ri]
        assert len(blob) <= nxt - hdr, "rec%d does not fit its slot (%d > %d)" % (
            ri, len(blob), nxt - hdr)
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
