# -*- coding: utf-8 -*-
"""Render the three status-bar labels with a real serif font.

harvest_labels.py built EP / FUNDS / SR POINTS out of glyphs harvested from
the game's own p04 art. That kept the exact house style, but the harvested
alphabet is tiny and uneven, and at 4x it reads as thin and cramped.

This renders the same three cells from a TTF instead, in the palette the
sheet already animates:
    15 = fill, 11 = edge (1px outline), 4 = shadow (offset 1,1), 0 = clear
Those are CLUT INDICES, not colours - the bar pulses gold by cycling the
palette, so the indices must be exact or the animation breaks.

    render_bar_labels.py preview            -> analysis/bar_labels_preview.png
    render_bar_labels.py iso <iso>          paint the cells into the ISO
    render_bar_labels.py ram                poke them into the running game
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont

KVM_LBA, SECTOR, ROWBYTES = 1289810, 2048, 128
P05 = 0x28B40
RAM_P05 = 0xC5A9E0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO_DEFAULT = os.path.join(WORK, "iso", "srwz_cap.bin")

# CLUT indices, not colours. The game applies its OWN palette to this sprite
# at draw time, so the CLUT embedded in the TIM2 is NOT what you see - index 8
# measures black in the embedded table yet renders olive in the bar, and index
# 11 is olive too. Do not reason from the embedded palette.
#
# The reliable source is the game's own art on the same sheet: sampling the
# "BS." cell (untranslated, sits in the same bar with the same palette) shows
# every glyph ringed in **index 1**, with a gold gradient inside. So:
#     1  = outline (the true black)
#     15 = fill
#     0  = clear
# The original harvested art used 11 = edge and 4 = shadow; both read as
# yellow-olive here, which is what looked wrong.
FILL, EDGE, CLEAR = 15, 1, 0
SHADOW = None                                # no drop shadow
OUTLINE = 2                                  # ring thickness in pixels
TRACK_PX = 0                                 # px added between glyph fills
SQUEEZE = 1.10                               # max horizontal squeeze allowed
INK_PAD = 2                                  # px of cell reserved for the ring

# The cells are NARROW: "Funds" gets 44 usable px, "SR Points" 83. Any normal
# face at the height we want is much wider than that, and squeezing it to fit
# (what the Times version did) collapses the counters - "n" came out as
# o##oo##o, i.e. the hole in the middle was solid outline, so every letter
# read as a dark blob.
#
# So the face has to be condensed (to fit at a decent height without any
# squeeze) AND open-countered (so a 1px ring on each side of a counter still
# leaves a clear pixel). Impact is condensed but its counters are far too
# tight - it scored 2 open counters in "SR Points" where Arial Narrow Bold
# scores 7 at the same height. Arial Narrow Bold also matches the weight of
# the game's own "BS." art.
FONT = r"C:\Windows\Fonts\ARIALNB.TTF"

# (cell x0,y0,x1,y1), text, ink HEIGHT ceiling, bottom row of the fill, left pad
#
# LEFT PAD exists because the cell is not all drawable. The game clips EP to
# roughly where the Japanese art sat (x146-165, rows 2-21 - dumped from
# srwz_jpall.bin), so ink painted at x142-145 never appears and the E looked
# sheared off. The pad keeps those columns empty while the cell itself stays
# the full width, so the old wider paint still gets cleared.
# The cells are width-limited (EP and Funds already touch both edges), so
# "bigger" means taller with a slight horizontal squeeze to fit - normal for
# pixel UI, and it keeps the sprite inside its own cell.
LABELS = [
    ((142,  2, 166, 30), "EP",        14, 16, 4),
    ((208,  0, 255, 32), "Funds",     14, 20, 0),
    ((148, 40, 235, 63), "SR Points", 14, 19, 0),
]


def load_page(iso_path, texoff=P05):
    with open(iso_path, "rb") as f:
        f.seek(KVM_LBA * SECTOR + texoff + 16 + 48)
        return bytearray(f.read(32768))


def clut(iso_path, texoff=P05):
    with open(iso_path, "rb") as f:
        f.seek(KVM_LBA * SECTOR + texoff + 16)
        tot, clutsz, img, hdr = struct.unpack("<IIIH", f.read(14))
        f.seek(KVM_LBA * SECTOR + texoff + 16 + hdr + img)
        return f.read(clutsz)


def _exterior(grid, w, h):
    """Clear pixels reachable from the border -> everything but the counters."""
    seen = [[False] * w for _ in range(h)]
    stack = [(y, x) for y in range(h) for x in (0, w - 1) if grid[y][x] == CLEAR]
    stack += [(y, x) for x in range(w) for y in (0, h - 1) if grid[y][x] == CLEAR]
    for y, x in stack:
        seen[y][x] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == CLEAR \
                    and not seen[ny][nx]:
                seen[ny][nx] = True
                stack.append((ny, nx))
    return seen


def render_cell(text, w, h, ink_h, bottom, left_pad=0):
    """-> [[index]] grid.

    The glyphs are rendered large, cropped to their ink, then scaled to
    `ink_h` tall - squeezed horizontally if that would overflow the cell -
    and seated so the ink's last row is `bottom`. Fill/edge/shadow need one
    spare pixel on each side, so the usable width is w-2.
    """
    PT = 96
    f = ImageFont.truetype(FONT, PT)

    def draw_string(track_hi):
        """The whole string on one canvas, `track_hi` extra px between chars.

        Drawn as one piece so the glyphs keep their real proportions - scaling
        each character to the same height turns 'u' and 'n' into capitals.
        """
        cvs = Image.new("L", (PT * (len(text) + 2), PT * 3), 0)
        d = ImageDraw.Draw(cvs)
        x = PT
        for ch in text:
            d.text((x, PT), ch, font=f, fill=255)
            x += int(round(d.textlength(ch, font=f))) + track_hi
        return cvs

    # Glyphs grow by OUTLINE on every side, so the fills need TRACK_PX + 2*
    # OUTLINE between them for two rings to stay apart. Tracking is applied
    # before the scale, so convert it back into high-res units first.
    # ink_h is a CEILING, not a promise: the height is stepped down until the
    # natural width fits the cell. Squeezing instead of shrinking is what
    # wrecked the Times version, so it is never done.
    # The glyph budget is deliberately NOT tied to OUTLINE: a thicker ring
    # must not shrink the letters (that made them smaller AND sealed the
    # counters). Rings 2+ grow outward only and simply clip at the cell edge.
    avail = w - 2 * INK_PAD - left_pad
    for trial in range(ink_h, 6, -1):
        base = draw_string(0).getbbox()
        scale = trial / float(base[3] - base[1])       # ascender-to-baseline
        hi = draw_string(max(0, int(round(TRACK_PX / scale))))
        ink = hi.crop(hi.getbbox())
        tw = max(1, int(round(ink.width * scale)))
        if tw <= avail * SQUEEZE:                      # a few % is invisible
            tw = min(tw, avail)
            break
    if trial != ink_h:
        print("  %s: %dpx would need %d px of width, using %dpx (%d wide)"
              % (text, ink_h, tw, trial, tw))
    ink_h = trial
    core = ink.resize((tw, ink_h), Image.LANCZOS).point(
        lambda v: 255 if v > 110 else 0)
    canvas = Image.new("L", (w, h), 0)
    canvas.paste(core, (left_pad + INK_PAD + (avail - tw) // 2,
                        max(0, bottom - ink_h + 1)))
    core = canvas
    px = core.load()
    grid = [[CLEAR] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if px[x, y]:
                grid[y][x] = FILL
    # Outline: OUTLINE successive 1px rings around the fill.
    #
    # Only the FIRST ring is grown everywhere. At this size a counter is about
    # 3px wide, so a second ring growing inwards from both stems would seal it
    # shut and the letter would go back to being a blob. Rings 2+ are
    # therefore grown only into pixels connected to the outside of the glyph,
    # which thickens the visible edge without touching the counters.
    N8 = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    for ring in range(OUTLINE):
        outside = _exterior(grid, w, h) if ring else None
        add = []
        for y in range(h):
            for x in range(w):
                if grid[y][x] != CLEAR:
                    continue
                if outside is not None and not outside[y][x]:
                    continue                            # inside a counter
                if any(0 <= y + dy < h and 0 <= x + dx < w
                       and grid[y + dy][x + dx] in (FILL, EDGE) for dy, dx in N8):
                    add.append((y, x))
        for y, x in add:
            grid[y][x] = EDGE
    if SHADOW is not None:
        for y in range(h - 1, 0, -1):
            for x in range(w - 1, 0, -1):
                if grid[y][x] == CLEAR and grid[y - 1][x - 1] in (FILL, EDGE):
                    grid[y][x] = SHADOW
    return grid


def cells(iso_path):
    out = []
    for (x0, y0, x1, y1), text, ink_h, bottom, left_pad in LABELS:
        x0 &= ~1
        w, h = x1 - x0, y1 - y0
        grid = render_cell(text, w, h, ink_h, bottom, left_pad)
        rows = []
        for yy, vals in enumerate(grid):
            row = bytearray()
            for xb in range(0, len(vals), 2):
                lo = vals[xb]
                hi = vals[xb + 1] if xb + 1 < len(vals) else 0
                row.append(lo | (hi << 4))
            rows.append(((y0 + yy) * ROWBYTES + x0 // 2, bytes(row)))
        out.append((text, (x0, y0, w, h), grid, rows))
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    iso_path = sys.argv[2] if len(sys.argv) > 2 else ISO_DEFAULT
    data = cells(iso_path)
    if mode == "preview":
        cl = clut(iso_path)
        idx = []
        for b in range(0, 256, 32):
            idx += list(range(b, b + 8)) + list(range(b + 16, b + 24)) + \
                   list(range(b + 8, b + 16)) + list(range(b + 24, b + 32))
        pal = [tuple(cl[i * 4:i * 4 + 3]) for i in idx[:16]]
        W = max(g[1][2] for g in data) + 8
        H = sum(g[1][3] + 4 for g in data) + 4
        im = Image.new("RGB", (W, H), (12, 12, 40))
        y = 2
        for text, (x0, y0, w, h), grid, rows in data:
            for yy in range(h):
                for xx in range(w):
                    v = grid[yy][xx]
                    if v:
                        im.putpixel((4 + xx, y + yy), pal[v])
            y += h + 4
        out = os.path.join(WORK, "analysis", "bar_labels_preview.png")
        im.resize((W * 6, H * 6), Image.NEAREST).save(out)
        print("preview -> %s" % out)
        return
    if mode == "iso":
        f = open(iso_path, "r+b")
        base = KVM_LBA * SECTOR + P05 + 16 + 48
        for text, box, grid, rows in data:
            for off, raw in rows:
                f.seek(base + off)
                f.write(raw)
        f.close()
        print("painted %d labels into %s" % (len(data), os.path.basename(iso_path)))
        return
    if mode == "ram":
        from pine_read import Pine
        p = Pine()
        n = 0
        for text, box, grid, rows in data:
            for off, raw in rows:
                addr = RAM_P05 + off
                a0 = addr & ~3
                a1 = (addr + len(raw) + 3) & ~3
                live = bytearray()
                for w in p.read32_batch(list(range(a0, a1, 4))):
                    live += w.to_bytes(4, "little")
                live[addr - a0:addr - a0 + len(raw)] = raw
                for i in range(0, len(live), 4):
                    p.write32(a0 + i, int.from_bytes(live[i:i + 4], "little"))
                    n += 1
        print("wrote %d words" % n)


if __name__ == "__main__":
    main()
