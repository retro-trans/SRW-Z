# -*- coding: utf-8 -*-
"""Resolve the voice/sequence records inside SRVC blocks.

A text block is a series of units: [misc][records][quote pool]. Each record is
an 8-byte cell in the pool:

    [u16 clip_id][u16 section_tag][u16 f2][00 00]

f2 is the byte offset of the record's target caption RELATIVE TO AN ANCHOR
SLOT - the first quote of the record's own unit. Both anchor and target are
strings, so after strings change length the relation can be recomputed:
new_f2 = new_off[target] - new_off[anchor]. That is what frees the captions
from the byte budget - see srvc_apply --free.

DETECTION IS DONE ON RAW POOL BYTES, in two passes:
1. seeds: cells whose parsed shape is unambiguous (a 6-byte string followed
   by an empty, or the 4B+1B split when f2's low byte is 0x00). Their section
   constants are fitted (f2 + C must land on a string boundary for EVERY seed
   of a section, C itself must be a slot offset; block-majority settles ties).
2. stride walk: records live in arrays, so from every seed walk the raw pool
   in +-8-byte steps, accepting a cell iff its trailing pad is 00 00 and its
   f2 resolves under the RUN's anchor. This catches every cell the string
   parser splits irregularly - a zero byte inside clip, section or f2 makes a
   cell parse as 5B, 4B+1B, or shorter fragments, and the shape pass alone
   missed 8,790 of 56,956 cells (the 0.8.54 Saegusa garbage caption).

resolve(blocks) -> (records, unresolved) where records is
    {block_index: [(pool_byte_pos, target_slot, anchor_slot), ...]}
`unresolved` lists (block_index, pool_byte_pos, reason). A block with any
unresolved record must fall back to the exact-byte-budget mode.
"""
import struct
from collections import Counter

from srvc_work import is_quote

MAX_CLIP = 34250


def pool_offsets(strings):
    offs, o = [], 0
    for s in strings:
        offs.append(o)
        o += len(s) + 1
    return offs


def seed_cells(strings, offs):
    """Yield (pool_pos, clip, f1, f2) for unambiguous record shapes."""
    i = 0
    n = len(strings)
    while i < n:
        s = strings[i]
        if len(s) == 6 and i + 1 < n and len(strings[i + 1]) == 0:
            clip, f1, f2 = struct.unpack("<3H", s)
            yield offs[i], clip, f1, f2
            i += 2
            continue
        if (len(s) == 4 and i + 2 < n and len(strings[i + 1]) == 1
                and len(strings[i + 2]) == 0):
            clip, f1, f2 = struct.unpack("<3H", s + b"\x00" + strings[i + 1])
            yield offs[i], clip, f1, f2
            i += 3
            continue
        i += 1


def resolve(blocks):
    records = {}
    unresolved = []
    for bi, b in enumerate(blocks):
        if not b.has_text:
            continue
        offs = pool_offsets(b.strings)
        omap = {offs[k]: k for k in range(len(b.strings))}
        P = b"\x00".join(b.strings) + b"\x00"
        seeds = [c for c in seed_cells(b.strings, offs) if c[1] < MAX_CLIP]
        if not seeds:
            continue

        # fit the anchor constant per section from the seeds
        by_sec = {}
        for pos, clip, f1, f2 in seeds:
            by_sec.setdefault(f1, []).append((pos, f2))
        sec_C = {}
        votes = Counter()
        for f1, recs in by_sec.items():
            cand = Counter()
            for _pos, f2 in recs:
                for qo in omap:
                    d = qo - f2
                    if 0 <= d < 1 << 16:
                        cand[d] += 1
            full = [c for c, cnt in cand.items()
                    if cnt == len(recs) and c in omap]
            full_q = [c for c in full if is_quote(b.strings[omap[c]])]
            pick = full_q or full
            if len(pick) == 1:
                sec_C[f1] = pick[0]
                votes[pick[0]] += len(recs)
            elif pick:
                sec_C[f1] = pick
        majority = votes.most_common(1)[0][0] if votes else None
        for f1 in list(sec_C):
            if isinstance(sec_C[f1], list):
                cs = sec_C[f1]
                sec_C[f1] = majority if majority in cs else cs[0]

        # collect cells: seeds first, then stride-walk each run
        cells = {}                       # pool_pos -> C (the run's anchor)
        for pos, clip, f1, f2 in seeds:
            C = sec_C.get(f1)
            if C is None:
                unresolved.append((bi, pos, "no consistent constant"))
                continue
            cells[pos] = C
        allC = sorted(set(cells.values()))
        for r0 in sorted(cells):
            for step in (8, -8):
                r = r0 + step
                C = cells[r0]
                while 0 <= r <= len(P) - 8 and r not in cells:
                    if P[r + 6:r + 8] != b"\x00\x00":
                        break
                    f2, = struct.unpack("<H", P[r + 4:r + 6])
                    if (f2 + C) in omap:
                        cells[r] = C
                    else:
                        # unit boundary inside a packed array: try the other
                        # anchors before giving up on the run
                        alt = [c for c in allC if (f2 + c) in omap]
                        if len(alt) == 1:
                            cells[r] = C = alt[0]
                        else:
                            break
                    r += step

        out = []
        for r, C in sorted(cells.items()):
            f2, = struct.unpack("<H", P[r + 4:r + 6])
            tgt = omap.get(f2 + C)
            if tgt is None:
                unresolved.append((bi, r, "target not on a boundary"))
            else:
                out.append((r, tgt, omap[C]))
        if out:
            records[bi] = out
    return records, unresolved


def new_position(r, offs_old, offs_new):
    """Map a pool byte position through a re-layout.

    The containing slot's content is unchanged (records are never quotes),
    so the byte keeps its offset within the slot.
    """
    import bisect
    k = bisect.bisect_right(offs_old, r) - 1
    return offs_new[k] + (r - offs_old[k])
