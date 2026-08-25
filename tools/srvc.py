"""Parse and rebuild BTL/SRVC.BIN using its companion BTL/SRVC.SEG.

SRVC.SEG is an array of u32 block offsets into SRVC.BIN; the final value is an
EOF sentinel, so block i spans [seg[i], seg[i+1]).

Block layout:
    +0x00  u16   0x4F00 marker
    +0x02  u16   group count
    +0x04  u16 / +0x06 u16   line counts -- NOT reliable, some blocks zero them
    +0x08  ...   grouping table, (u16 first_line, u8 line_count, u8 tag)
    I      n1 x (u32 id, u32 offset)   offsets relative to the string pool
    S      n2 x null-terminated Shift-JIS strings
           zero padding to the end of the block

Because the header counts lie, the index and pool are located empirically: we
look for a position whose offset field is 0, walk the index forward while the
offsets stay sane, then require the resulting string pool to tile exactly to
the end of the block with only zero padding left over. A wrong guess fails
that tiling test almost immediately.
"""
import struct

MARKER = b"\x00\x4F"
PAD_MAX = 64


class Block(object):
    __slots__ = ("start", "raw", "head", "ids", "slots", "strings", "pad")

    def __init__(self):
        self.raw = None      # set for blocks we keep verbatim
        self.head = b""
        self.ids = []
        self.slots = []      # index entry k points at strings[slots[k]]
        self.strings = []
        self.pad = b""

    @property
    def has_text(self):
        return self.raw is None


def read_seg(seg_data):
    n = len(seg_data) // 4
    return [struct.unpack("<I", seg_data[i * 4:i * 4 + 4])[0] for i in range(n)]


def _tile_strings(data, pool, limit):
    """Read null-terminated strings from `pool`; they must tile to the end of
    the block leaving only zero padding. Returns (strings, offsets, end)."""
    strings, offsets = [], []
    pos = pool
    while pos < limit:
        end = data.find(b"\x00", pos, limit)
        if end == -1:
            return None
        # a run of zeros this long means we've reached the padding
        if end == pos and limit - pos <= PAD_MAX and not any(data[pos:limit]):
            break
        strings.append(data[pos:end])
        offsets.append(pos - pool)
        pos = end + 1
    if not strings:
        return None
    if limit - pos > PAD_MAX or any(data[pos:limit]):
        return None
    return strings, offsets, pos


def _try_at(data, cand, limit):
    """Treat `cand` as the index start and try to validate the whole tail."""
    # walk the index forward while entries look like (id, ascending offset)
    n1 = 0
    prev = -1
    p = cand
    while p + 8 <= limit:
        ident, off = struct.unpack("<II", data[p:p + 8])
        if off < prev or off > limit - cand:
            break
        prev = off
        n1 += 1
        p += 8
        r = _tile_strings(data, p, limit)
        if r:
            strings, real_offs, end = r
            slot_of = dict((o, i) for i, o in enumerate(real_offs))
            ids, offs = [], []
            ok = True
            for k in range(n1):
                i2, o2 = struct.unpack("<II", data[cand + k * 8: cand + k * 8 + 8])
                if o2 not in slot_of:
                    ok = False
                    break
                ids.append(i2)
                offs.append(slot_of[o2])
            if ok and len(strings) >= n1 * 0 + 1:
                return ids, offs, strings, end
    return None


def parse(data, seg):
    blocks = []
    for bi in range(len(seg) - 1):
        start, limit = seg[bi], seg[bi + 1]
        b = Block()
        b.start = start
        hit = None
        if data[start:start + 2] == MARKER and limit - start >= 16:
            for cand in range(start + 8, limit - 8, 4):
                if struct.unpack("<I", data[cand + 4:cand + 8])[0] != 0:
                    continue
                r = _try_at(data, cand, limit)
                if r:
                    hit = (cand, r)
                    break
        if hit is None:
            b.raw = data[start:limit]
        else:
            cand, (ids, slots, strings, end) = hit
            b.head = data[start:cand]
            b.ids = ids
            b.slots = slots
            b.strings = strings
            b.pad = data[end:limit]
        blocks.append(b)
    return blocks


def build(blocks):
    """Re-emit (bin, seg) with every offset recomputed."""
    out = bytearray()
    offsets = []
    for b in blocks:
        offsets.append(len(out))
        if not b.has_text:
            out += b.raw
            continue
        out += b.head
        offs, running = [], 0
        for s in b.strings:
            offs.append(running)
            running += len(s) + 1
        for k, ident in enumerate(b.ids):
            out += struct.pack("<II", ident, offs[b.slots[k]])
        for s in b.strings:
            out += s + b"\x00"
        out += b.pad
    offsets.append(len(out))
    return bytes(out), b"".join(struct.pack("<I", o) for o in offsets)
