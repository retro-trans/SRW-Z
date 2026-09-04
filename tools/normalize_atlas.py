# -*- coding: utf-8 -*-
"""Even out glyph spacing in a 2bpp hwatlas.

The generator centres each glyph in the 12px cell, so a narrow glyph (i, l, !, .)
carries several blank columns on its left, and since the advance is measured from
the cell's left edge those blanks read as extra letter-spacing before the glyph.

This left-aligns every glyph to a 1px bearing. With a FLOOR it also BALANCES the
narrow ones: a glyph whose natural advance (ink_right+2) is under the floor is
shifted right by half the shortfall, so the extra room the floor adds sits evenly
on both sides instead of all trailing. Re-measure advances with patch_vwf_widths,
then floor the table with floor_advance_table.py to the same value.

Usage: normalize_atlas.py <in.bin> <out.bin> [floor]   (floor 0 = plain left-align)
"""
import sys

CW, CH, NART, GB = 12, 24, 69, 72


def decode(cell):
    px = []
    for r in range(CH):
        b = cell[r * 3:r * 3 + 3]
        bits = (b[0] << 16) | (b[1] << 8) | b[2]
        px.append([(bits >> (22 - 2 * x)) & 3 for x in range(CW)])
    return px


def encode(px):
    out = bytearray()
    for r in range(CH):
        bits = 0
        for x in range(CW):
            bits |= (px[r][x] & 3) << (22 - 2 * x)
        out += bytes([(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF])
    return bytes(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    floor = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    raw = open(src, "rb").read()
    assert len(raw) == NART * GB, "not a %d-byte atlas" % (NART * GB)
    out = bytearray()
    moved = 0
    for g in range(NART):
        px = decode(raw[g * GB:(g + 1) * GB])
        cols = [x for x in range(CW) if any(px[r][x] for r in range(CH))]
        if not cols:                       # empty glyph (space): leave as-is
            out += raw[g * GB:(g + 1) * GB]
            continue
        width = cols[-1] - cols[0] + 1
        target = 1                         # left bearing = 1
        # balance: if left-aligned advance (width+2) is under the floor, push
        # the glyph right by half the shortfall so both sides get the room
        la_adv = width + 2
        if floor and la_adv < floor:
            target = 1 + (floor - la_adv) // 2
        # never push the right edge off the 12px cell
        target = min(target, (CW - 1) - (width - 1))
        shift = cols[0] - target           # >0 move left, <0 move right
        if shift == 0:
            out += raw[g * GB:(g + 1) * GB]
            continue
        new = [[0] * CW for _ in range(CH)]
        for r in range(CH):
            for x in range(CW):
                nx = x - shift
                if 0 <= nx < CW:
                    new[r][nx] = px[r][x]
        out += encode(new)
        moved += 1
    assert len(out) == NART * GB
    open(dst, "wb").write(out)
    print("normalized %d/%d glyphs (floor=%d) -> %s" % (moved, NART, floor, dst))


main()
