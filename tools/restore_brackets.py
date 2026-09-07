# -*- coding: utf-8 -*-
u"""Put 「」 back on dialogue lines that lost them.

WHY IT MATTERS: the Back Log draws the raw string with no name plate, and only
「」 colours the speaker's name. A line without them shows as flat white text,
so a row whose japanese has 「」 and whose english does not is a defect - see
[[backlog-needs-speech-delimiter]] and [[debracketing-the-script]].

The brackets cost 4 bytes and about 2 columns, so every row is re-wrapped to
its own box and checked against its slot; anything that no longer fits is
REPORTED, never truncated. Straight quotes around a whole body are replaced by
「」 rather than wrapped again.

Rows whose japanese uses （ ）, and rows whose english is already bracketed in
any style, are left alone.

Usage: restore_brackets.py <iso> <jp-iso> [--write] [--only REC]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import reflow_dialogue as R
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X
import struct

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = "\n"
OPEN, CLOSE = "「", "」"


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def wrap(field, over, adv):
    sp, _, body = field.partition(NL)
    body = body.strip()
    if body[:1] == OPEN and body[-1:] == CLOSE:
        lb, rb, inner = OPEN, CLOSE, body[1:-1]
    elif body[:1] == "(" and body[-1:] == ")":
        lb, rb, inner = "(", ")", body[1:-1]
    else:
        lb, rb, inner = "", "", body
    inner = inner.replace(NL, " ").strip()
    wl = R.reflow(inner, (R.OVERMAP_PX if over else R.SCENE_PX) - 21, adv)
    if not wl:
        wl = [""]
    wl[0] = lb + wl[0]
    wl[-1] = wl[-1] + rb
    return (sp + NL + NL.join(wl)) if sp else NL.join(wl), len(wl)


def free_gaps(d, jb):
    """Free runs inside the record that are safe to write text into.

    Only NUL runs that the japanese holds TEXT or text padding in are usable.
    A japanese zero anywhere else is structure - index tables, event data - and
    writing a string over it is what froze stage 19 (see fix_struct_intrusions).
    """
    m = X.safe_mask(jb)
    n = min(len(d), len(jb))
    gaps = []
    i = 0
    while i < n:
        if d[i] == 0 and m[i]:
            s = i
            while i < n and d[i] == 0 and m[i]:
                i += 1
            # The FIRST zero of a run terminates the string before it. Writing
            # there runs that string into whatever we place, so the free space
            # starts one byte later.
            if s > 0 and d[s - 1] != 0:
                s += 1
            if i - s >= 4:
                gaps.append([s, i])
        else:
            i += 1
    return gaps


def relocate(d, jb, off, nb, pm, protected, gaps, moved_words, mask=None):
    """Move one field into a gap and repoint it. Returns True on success."""
    need = len(nb) + 1
    words = [w for w in pm.get(off, []) if w not in protected]
    if not words:
        return False                      # nothing we may repoint
    # BEST FIT: the smallest gap that takes it. Taking the first gap in
    # address order spends a 200-byte run on a 20-byte line and then has
    # nothing left for the long ones - the same trap fix_stranded_strings hit.
    for g in sorted(gaps, key=lambda g: g[1] - g[0]):
        if g[1] - g[0] < need:
            continue
        dst = g[0]
        delta = dst - off
        z = d.find(b"\x00", off)
        # The space must still be empty. A gap list computed before other
        # edits goes stale the moment a field grows into its own padding, and
        # writing there silently ate the string in front of it.
        assert all(d[x] == 0 for x in range(dst, dst + need)), \
            "gap %#x..%#x is not free" % (dst, dst + need)
        d[dst:dst + need] = nb + b"\x00"
        for w in words:
            old = struct.unpack_from("<I", d, w)[0]
            struct.pack_into("<I", d, w, old + delta)
        for x in range(off, z):
            d[x] = 0
        g[0] += need
        # the span it vacated is free now - hand it back, so a later line can
        # use it. Without this the record runs out of room after ~10 moves.
        rs = off + 1 if (off > 0 and d[off - 1] != 0) else off
        if mask is not None and z - rs >= 4 and all(mask[x] for x in range(rs, z)):
            gaps.append([rs, z])
        moved_words.update(words)
        return True
    return False


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None

    adv = R.load_adv(iso)
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    jp = [d for h, d in banlz.decompress_all(load(jpiso))
          if isinstance(h, int) and d is not None]

    found = fixed = riders = 0
    nofit = []
    touched = {}
    relocated = {}
    for ri, (hdr, d) in enumerate(live):
        if only is not None and ri != only:
            continue
        eb = bytes(d)
        jb = bytes(jp[ri])
        m = EP.pair(eb, jb)
        bm = R.boxmap(d)
        pm = F.pointer_map(eb)
        smask = X.safe_mask(jb)
        protected = X.struct_words(jb, smask)
        gaps = free_gaps(d, jb)
        before = {w: F.text_at(eb, v) for v, ws in pm.items() for w in ws
                  if w not in protected}
        moved = 0
        moved_words = set()
        changed = False
        pending = []
        for off in sorted(m):
            et, _ = EP.text_at(eb, off)
            if not et or NL not in et:
                continue
            jt, _ = EP.text_at(jb, m[off][0])
            if not jt or OPEN not in jt:
                continue
            # The japanese must be a SPEECH field: a speaker plate on the first
            # line, then a body that opens and closes with 「」. Encyclopedia
            # prose quotes something mid-paragraph and has no plate, and adding
            # brackets to it would be wrong (rec1, rec25 unit descriptions).
            jsp, _, jbody = jt.partition(NL)
            jbody = jbody.replace("　", "").replace(NL, "").strip()
            if OPEN in jsp or not jbody.startswith(OPEN) or not jbody.endswith(CLOSE):
                continue
            sp, _, body = et.partition(NL)
            body = body.strip()
            if not body:
                continue
            if body[0] in (OPEN, "(", "（"):
                continue                       # already bracketed
            # A line that quotes something inside itself already carries 「」;
            # wrapping it again produces a doubled 」」 (rec2, rec47).
            if OPEN in body or CLOSE in body:
                continue
            found += 1
            # A second pointer aimed INSIDE this field (at its second line,
            # say) cannot survive the edit: adding 「 shifts every inner offset
            # and re-wrapping moves the line breaks. Leave those rows alone.
            zt = eb.find(b"\x00", off)
            if any(off < v < zt for v in pm):
                riders += 1
                continue
            if body[0] == '"' and body[-1:] == '"':
                body = body[1:-1].strip()      # straight quotes -> 「」
            new = sp + NL + OPEN + body.replace(NL, " ") + CLOSE
            over = bm.get(off, 1) == 1
            nf, nl = wrap(new, over, adv)
            nb = nf.encode("cp932", "replace")
            z = d.find(b"\x00", off)
            e = z
            while e < len(d) and d[e] == 0:
                e += 1
            slot = e - off - 1
            if nl > 3:
                nofit.append((ri, off, len(nb), slot, nl,
                              et.replace(NL, " / ")[:55]))
                continue
            pending.append((off, nb, nl, slot, et))

        # Everything that already fits goes first: each one frees the tail of
        # its own slot. Then the movers, LARGEST FIRST, so the long lines get
        # the big runs instead of finding them spent on short ones.
        for off, nb, nl, slot, et in pending:
            if len(nb) <= slot:
                d[off:off + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
                moved_words.update(pm.get(off, []))   # its text legitimately changed
                fixed += 1
                changed = True
        # Recompute the free space now: the writes above grew fields into the
        # padding the first scan had counted as free.
        gaps = free_gaps(d, jb)
        for off, nb, nl, slot, et in sorted(pending, key=lambda x: -len(x[1])):
            if len(nb) <= slot:
                continue
            if relocate(d, jb, off, nb, pm, protected, gaps, moved_words, smask):
                fixed += 1
                moved += 1
                changed = True
            else:
                nofit.append((ri, off, len(nb), slot, nl,
                              et.replace(NL, " / ")[:55]))

        if changed:
            # nothing else may have shifted: every pointer that resolved to a
            # string still resolves, and structure pointers are untouched.
            for w in protected:
                assert d[w:w + 4] == eb[w:w + 4], \
                    "rec%d structure pointer %#x moved" % (ri, w)
            nd = bytes(d)
            for w, t in before.items():
                nv = struct.unpack_from("<I", nd, w)[0] - F.BASE
                got = F.text_at(nd, nv)
                if w in moved_words:
                    assert got is not None, \
                        "rec%d moved word %#x stopped resolving" % (ri, w)
                else:
                    assert got == t, \
                        "rec%d word %#x no longer resolves to its text" % (ri, w)
            relocated[ri] = moved
            touched[ri] = bytes(d)

    print("rows missing their brackets : %d" % found)
    print("re-bracketed                : %d (%d moved to free space)"
          % (fixed, sum(relocated.values())))
    print("skipped, inner pointer      : %d" % riders)
    print("did not fit (left as-is)    : %d" % len(nofit))
    for x in nofit[:40]:
        print("   rec%-4d @%#07x %d B > slot %d, %d line(s)  %r" % x)
    if not touched or not write:
        if touched:
            print("\n(dry run - pass --write to apply)")
        return 0

    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(touched[ri])
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(touched[ri])
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
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


raise SystemExit(main())
