# -*- coding: utf-8 -*-
"""COMPDATA string pool: enumerate, repack, and repoint.

THE FINDING (2026-08-26). Weapon/ability/item names are NOT walked and NOT
indexed. COMPDATA.BN's single 524,032-byte record ends in a string pool, and
every string is reached through an ABSOLUTE PS2 RAM POINTER stored earlier in
the same record. The record is loaded at a hardcoded 0x006D6800 and used in
place - file bytes and RAM bytes at the pointer tables are byte-for-byte
identical, so nothing is relocated at load time.

That is why the byte budget looked immovable: every static search for an index,
a record-relative offset, or an offset/8 failed, because the stored value is
0x0073xxxx. Growing a name in place left the NEXT string's pointer aimed into
the middle of the new text - the "Musou Sword" / "ord" result.

Layout, measured on the pristine JP COMPDATA:

    0x00904 .. 0x61658   pointer tables (9,483 pointer words)
    0x61680 .. 0x7FF00   string pool    (3,435 entries, all 8-byte aligned)

The two never overlap, every pool entry is referenced by at least one pointer,
and nothing outside COMPDATA holds a pointer into the pool (checked against the
ELF on disc and against a 32MB EE RAM dump - the only apparent hits are u16
pairs whose high half is 0x0074, e.g. `00 a2 74 00`).

So the pool can be repacked freely as long as every pointer is rewritten with
it. Packed tightly on the 8-byte grid the pool reclaims 22,332 bytes, which is
the budget available for longer names.

91 pointer-SHAPED words do not land on a string start. That looks like u16 pairs
reading as an address by coincidence - and for 34 of them it is. For the other
60 it is NOT: they sit precisely on a pointer-table stride, so they are real
table entries pointing either into a string's NUL PADDING (a deliberate EMPTY
string, used to draw a blank slot) or a few bytes INTO a string (a deliberate
substring). 0.8.81 left them alone on the coincidence argument and broke all 60;
tools/fix_pool_strays.py repaired them in 0.8.90.

repack() now runs that stride test and REFUSES rather than repeating it. The
check costs one pass over data already in hand, which is what the original
assumption should have cost before being written down as fact.
"""
import struct

BASE = 0x006D6800          # hardcoded load address of the record
REC_LEN = 0x7FF00
POOL_LO, POOL_HI = 0x61680, 0x7FF00
GRID = 8
NUL = b"\x00"


def entries(rec, lo=POOL_LO, hi=POOL_HI):
    """[(start, text_bytes, slot_len)] over the pool, in address order."""
    out, p = [], lo
    while p < hi:
        e = rec.find(NUL, p)
        if e < 0 or e >= hi:
            break
        k = e
        while k < hi and rec[k] == 0:
            k += 1
        if e > p:
            out.append((p, bytes(rec[p:e]), k - p))
        p = k
    return out


def pointers(rec, starts):
    """[(word_pos, target_off)] for every 4-aligned word that resolves to a
    pool string start. Only the region before the pool is scanned: no pointer
    table lives inside the pool, and scanning the pool would corrupt text that
    happens to read as an address."""
    out = []
    for p in range(0, POOL_LO, 4):
        v = struct.unpack_from("<I", rec, p)[0]
        if BASE <= v < BASE + REC_LEN:
            t = v - BASE
            if t in starts:
                out.append((p, t))
    return out


def stray_pointers_on_a_stride(rec, starts):
    """Strays that sit on a pointer-table stride, i.e. REAL pointers.

    A stray is a pointer-shaped word not landing on a string start. Most are
    u16 pairs. But if a CONFIRMED pointer sits at the same stride either side of
    it, it is a table entry - it points into a string's padding (an empty
    string) or into its middle (a substring), and repacking will break it."""
    import collections
    ptrs = pointers(rec, starts)
    ws = set(p for p, _ in ptrs)
    pos = [p for p, _ in ptrs]
    gaps = collections.Counter(b - a for a, b in zip(pos, pos[1:]))
    strides = [g for g, n in gaps.most_common(8) if n > 20]
    out = []
    for p, t in strays(rec, starts):
        if any((p - s) in ws or (p + s) in ws for s in strides):
            out.append((p, t))
    return out


def strays(rec, starts):
    """Pointer-shaped words that do NOT land on a string start (the u16 pairs).
    Returned so callers can assert none of them fall inside the pool range that
    is about to move."""
    out = []
    for p in range(0, POOL_LO, 4):
        v = struct.unpack_from("<I", rec, p)[0]
        if BASE + POOL_LO <= v < BASE + REC_LEN and (v - BASE) not in starts:
            out.append((p, v - BASE))
    return out


def repack(rec, replace=None, allow_stray=False):
    """Return a new record with the pool packed tightly and every pointer
    rewritten. `replace` maps an ORIGINAL pool offset to new bytes.

    Raises ValueError if the repacked pool does not fit."""
    replace = replace or {}
    ent = entries(rec)
    starts = set(a for a, _, _ in ent)
    ptrs = pointers(rec, starts)
    if not ent:
        raise ValueError("no pool entries found")
    for off in replace:
        if off not in starts:
            raise ValueError("replacement offset %#x is not a string start" % off)

    onstride = stray_pointers_on_a_stride(rec, starts)
    if onstride and not allow_stray:
        raise ValueError(
            "%d pointer-shaped words sit on a pointer-table stride and point "
            "into padding or mid-string - they are REAL pointers and repacking "
            "would break them (this is the 0.8.81 bug). Repair them with "
            "fix_pool_strays.py, or pass allow_stray=True if they have already "
            "been accounted for. First few: %s"
            % (len(onstride), [(hex(p), hex(t)) for p, t in onstride[:4]]))
    seen = set(t for _, t in ptrs)
    orphan = starts - seen
    if orphan:
        raise ValueError("%d pool strings have no pointer: %s"
                         % (len(orphan), [hex(x) for x in sorted(orphan)[:5]]))

    # lay the pool out again, same order, 8-byte grid
    newoff, cur = {}, POOL_LO
    for off, text, _ in ent:
        body = replace.get(off, text)
        if NUL in body:
            raise ValueError("replacement for %#x contains a NUL" % off)
        newoff[off] = cur
        cur += ((len(body) + 1 + GRID - 1) // GRID) * GRID
    if cur > POOL_HI:
        raise ValueError("repacked pool needs %d bytes, pool is %d (over by %d)"
                         % (cur - POOL_LO, POOL_HI - POOL_LO, cur - POOL_HI))

    out = bytearray(rec)
    out[POOL_LO:POOL_HI] = NUL * (POOL_HI - POOL_LO)
    for off, text, _ in ent:
        body = replace.get(off, text)
        q = newoff[off]
        out[q:q + len(body)] = body
    for pos, t in ptrs:
        struct.pack_into("<I", out, pos, BASE + newoff[t])

    if len(out) != len(rec):
        raise ValueError("record length changed")
    verify(bytes(out), rec, ent, replace, newoff, ptrs)
    return bytes(out), cur, newoff


def verify(new, old, old_ent, replace, newoff, oldp):
    """Every ORIGINAL pointer word must now resolve to exactly the intended text.

    Checked by position, not by re-scanning: repacking moves the string starts,
    so some of the 91 stray u16 pairs come to look like valid pointers by
    coincidence. They are not pointers and are not rewritten; counting them
    would fail a correct repack."""
    ent = entries(new)
    got = {a: t for a, t, _ in ent}
    if len(ent) != len(old_ent):
        raise ValueError("entry count changed: %d -> %d" % (len(old_ent), len(ent)))
    for off, text, _ in old_ent:
        body = replace.get(off, text)
        q = newoff[off]
        if got.get(q) != body:
            raise ValueError("text mismatch at %#x: %r != %r" % (q, got.get(q), body))
    for pos, t in oldp:
        v = struct.unpack_from("<I", new, pos)[0]
        if v != BASE + newoff[t]:
            raise ValueError("pointer at %#x -> %#010x, expected %#010x"
                             % (pos, v, BASE + newoff[t]))
        if (v - BASE) not in got:
            raise ValueError("pointer at %#x lands off a string start" % pos)
    if new[:POOL_LO] != _mask(old[:POOL_LO], oldp) or True:
        pass
    # nothing outside the pool may change except the pointer words themselves
    ow = set(p for p, _ in oldp)
    for p in range(0, POOL_LO, 4):
        if p in ow:
            continue
        if new[p:p + 4] != old[p:p + 4]:
            raise ValueError("non-pointer word at %#x was modified" % p)


def _mask(b, ptrs):
    return b
