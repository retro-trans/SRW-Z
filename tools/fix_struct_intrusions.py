# -*- coding: utf-8 -*-
u"""Move STAGE strings that were parked over structure fields back into real text slack.

THE DEFECT (found 2026-09-07 from a hang after Gain's 「Sorry I'm late, Chief!」,
rec43): fix_stranded_strings.py (0.9.38) took the zeros after ANY pointer target
that passed is_text() as free slack. A pointer into a structure whose first
bytes happen to be non-zero and cp932-decodable (rec43 0x1AA0: c0 7e 75 00, a
pointer word) looks like a 3-byte "string" followed by 16 bytes of "slack" -
which are really the zero fields of a lookup table of (index, pointer) pairs.
A 15-byte line was written there, so index 0 of the table read as `.」\0` and
the script's lookup for group 0 (Gain and Emperanza entering) never returned:
the game stops advancing while the cursor keeps animating. 26 records carry
the same kind of intrusion (15-byte strings in 16-byte gaps, 31-byte strings in
32-byte gaps), all present since 0.9.38.

THE RULE: a zero byte of the japanese record is free ONLY if it is the padding
after a japanese TEXT string (a pointer target that decodes as cp932, is at least
4 bytes and contains a 2-byte SJIS character or a newline). Every other japanese
zero is structure and must still be zero in ours. Strings sitting on structural
zeros are moved into slack after an english TEXT string that itself lies on
japanese text or japanese text padding, and their pointer words repointed.

Usage: fix_struct_intrusions.py <iso> [--write] [--only REC]
       fix_struct_intrusions.py <iso> --check      (gate: exit 1 on any intrusion)
"""
import collections
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import fix_stranded_strings as F

SEC, LBA, SIZE, BASE = F.SEC, F.LBA, F.SIZE, F.BASE
JP_ISO = F.JP_ISO


def is_real_text(t):
    """Stricter than F.is_text: a dialogue/narration string, not a struct word."""
    if not F.is_text(t) or len(t) < 4:
        return False
    if b"\n" in t:
        return True
    i = 0
    while i < len(t):
        c = t[i]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            return True
        i += 1
    # pure ASCII english line of some length is text too
    return len(t) >= 6 and all(0x20 <= c < 0x7F or c == 0x0A for c in t)


def text_targets(b):
    """top-level real-text pointer targets (offset -> words), riders merged."""
    pm = F.pointer_map(b)
    tops, riders = [], collections.defaultdict(list)
    for v in sorted(pm):
        if tops and v <= tops[-1] + len(F.text_at(b, tops[-1])):
            riders[tops[-1]].append(v)
        else:
            tops.append(v)
    return pm, [v for v in tops if is_real_text(F.text_at(b, v))], riders


def safe_mask(jb):
    """1 where a byte of the japanese record is text, or a zero run that is
    bracketed by real text on BOTH sides (inter-field padding of the pool).
    A zero run that follows anything else - a pointer word, a struct - is
    structure, however text-like the bytes before it look."""
    m = bytearray(len(jb))
    _, tops, _ = text_targets(jb)
    tops = sorted(tops)
    ends = {}
    for v in tops:
        z = jb.find(b"\x00", v)
        m[v:z + 1] = b"\x01" * (z + 1 - v)
        ends[v] = z + 1
    starts = set(tops)
    for v in tops:
        e = ends[v]
        q = e
        while q < len(jb) and jb[q] == 0:
            q += 1
        if q < len(jb) and q in starts:
            m[e:q] = b"\x01" * (q - e)
    return m


def intrusions(eb, jb):
    """english pointer-target strings that overlap a structural japanese zero."""
    m = safe_mask(jb)
    n = min(len(eb), len(jb))
    pm, tops, riders = text_targets(eb)
    out = []
    for v in tops:
        t = F.text_at(eb, v)
        # A string whose START sits on a structural japanese zero was parked
        # there by a tool. One that starts on japanese text and merely runs
        # longer into its slot's padding is a slot-sized replacement - fine.
        if v < n and jb[v] == 0 and not m[v]:
            out.append((v, len(t)))
    return out


def struct_words(jb, m):
    """word offsets that hold a STRUCTURE pointer in the japanese record.

    These must keep their japanese value. A parked string covers rows of the
    table it sits in, so a word pointing at such a row looks (in OUR record)
    like a pointer into the middle of that string - a "rider" - and gets
    repointed along with it. That is what 0.9.67 did to rec43 0x1dc0, the
    enemy-group table pointer: enemy turns ended instantly because the group
    list resolved to text. Never repoint a word whose JAPANESE target is not
    text.
    """
    out = set()
    n = len(jb)
    for o in range(0, n - 3, 4):
        if m[o] or m[o + 3]:
            continue
        t = struct.unpack_from("<I", jb, o)[0] - BASE
        if 0 <= t < n and not m[t]:
            out.add(o)
    return out


def fix_record(eb, jb):
    bad = intrusions(eb, jb)
    if not bad:
        return None
    d = bytearray(eb)
    pm, tops, riders = text_targets(bytes(d))
    m = safe_mask(jb)
    protected = struct_words(jb, m)
    JPEND = len(jb)

    # only strings that are genuine pointer targets can be moved
    movable, other = [], []
    for s, n in bad:
        if s in pm and is_real_text(F.text_at(d, s)):
            movable.append(s)
        else:
            other.append((s, n))

    raw_gaps = []
    for v in tops:
        if v in movable or v >= JPEND:
            continue
        t = F.text_at(d, v)
        a = v + len(t) + 1
        e = min(F.slot_end(d, v), JPEND)
        # shrink to the part that is japanese text / text padding
        while a < e and not m[a]:
            a += 1
        while e > a and not m[e - 1]:
            e -= 1
        if e - a >= 2:
            raw_gaps.append([a, e])
    raw_gaps.sort()
    gaps = []
    for g in raw_gaps:
        if gaps and g[0] <= gaps[-1][1]:
            gaps[-1][1] = max(gaps[-1][1], g[1])
        else:
            gaps.append(g)

    before = {w: F.text_at(d, v) for v, ws in pm.items() for w in ws
              if w not in protected}
    moved, unplaced = [], []
    for v in sorted(movable, key=lambda v: -len(F.text_at(d, v))):
        t = F.text_at(d, v)
        need = len(t) + 1
        gaps.sort(key=lambda g: g[1] - g[0])
        for g in gaps:
            if g[1] - g[0] >= need:
                dst = g[0]
                delta = dst - v
                d[dst:dst + need] = t + b"\x00"
                words = list(pm[v])
                for r in riders.get(v, []):
                    words += pm[r]
                words = [w for w in words if w not in protected]
                for w in words:
                    old = struct.unpack_from("<I", d, w)[0]
                    struct.pack_into("<I", d, w, old + delta)
                d[v:v + need] = jb[v:v + need]        # restore the japanese bytes
                g[0] += need
                moved.append((v, dst, len(t), len(words)))
                break
        else:
            unplaced.append((v, len(t)))

    for w, t in before.items():
        nv = struct.unpack_from("<I", d, w)[0] - BASE
        assert F.text_at(d, nv) == t, "word %#x no longer resolves to its text" % w
    # Structure pointers must come out of this pass exactly as they went in.
    # (A few differ from the japanese since before 0.9.50 - rec29, rec109,
    # rec139; that is not this tool's business, and the game plays with them.)
    for w in protected:
        assert d[w:w + 4] == eb[w:w + 4], "structure pointer %#x drifted" % w
    return bytes(d), moved, unplaced, other


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    check = "--check" in sys.argv
    only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None

    jp = [(h, bytes(x)) for h, x in banlz.decompress_all(F.load(JP_ISO))
          if isinstance(h, int) and x is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytes(x)) for h, x in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and x is not None]
    heads = sorted(h for h, _ in live)

    if check:
        tot = 0
        for ri in range(min(len(live), len(jp))):
            bad = intrusions(live[ri][1], jp[ri][1])
            for s, n in bad:
                tot += 1
                print("  rec%-4d @%#06x %3d bytes  %r" % (ri, s, n, live[ri][1][s:s + 40]))
        print("struct intrusions: %d  %s" % (tot, "OK" if tot == 0 else "FAIL"))
        f.close()
        return 0 if tot == 0 else 1

    touched, tot_moved, tot_unplaced, tot_other = {}, 0, [], []
    for ri in range(min(len(live), len(jp))):
        if only is not None and ri != only:
            continue
        res = fix_record(live[ri][1], jp[ri][1])
        if res is None:
            continue
        nb, moved, unplaced, other = res
        touched[ri] = nb
        tot_moved += len(moved)
        tot_unplaced += [(ri, v, n) for v, n in unplaced]
        tot_other += [(ri, s, n) for s, n in other]
        for v, dst, n, k in moved:
            print("  rec%-4d %#06x -> %#06x  %3d bytes  %d word(s)  %s" % (
                ri, v, dst, n, k, F.text_at(live[ri][1], v).decode("cp932", "replace")
                .replace("\n", " / ")[:60]))
    print("\nrecords touched : %d" % len(touched))
    print("strings moved   : %d" % tot_moved)
    print("UNPLACED        : %d" % len(tot_unplaced))
    for ri, v, n in tot_unplaced:
        print("   rec%-4d @%#06x %3d bytes" % (ri, v, n))
    print("NOT A POINTER TARGET (left as is, inspect): %d" % len(tot_other))
    for ri, s, n in tot_other:
        print("   rec%-4d @%#06x %3d bytes %r" % (ri, s, n, live[ri][1][s:s + 24]))

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
        for ri, blob in ex.map(F._compress, [(r, n - h, d) for r, h, n, d in jobs]):
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
