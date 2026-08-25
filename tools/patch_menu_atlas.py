# -*- coding: utf-8 -*-
"""Replace the Japanese intermission-menu labels in the KURODATA_KVMDATA.BIN
UI texture atlas (TIM2 image #6, 256x256 4bpp) with English text.

The labels are pre-rendered graphics, not strings, so translating them means
redrawing pixels inside each label's UV rect. We keep the original palette
INDICES (fill/outline/highlight) so the game's per-CLUT tinting still works,
and we never move or resize anything - each label is redrawn inside its own
rect, so the file stays byte-identical in size and no pointers change.

Usage: patch_menu_atlas.py <src_kvmdata> <dst_kvmdata> [preview.png]
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont

TIM_OFF = 0x030D80
FILL, OUTLINE, HILITE = 14, 8, 7

# (x0, y0, x1, y1, english, allcaps_style)
LABELS = [
    (4,   1, 207,  30, "INTERMISSION"),
    (2, 107, 209, 133, "INTERMISSION"),
    (2, 138,  60, 156, "Units"),
    (139, 138, 232, 156, "Pilots"),
    (4, 163,  58, 180, "Bazaar"),
    (65, 162, 158, 180, "Next Map"),
    (3, 187,  96, 204, "Options"),
    (5, 210,  84, 228, "Squads"),
    (5, 234, 106, 252, "Data"),
]

# Regular weight, not bold: the bold face plus a full 8-way outline read far too
# heavy against the game's own lettering.
FONTS = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf",
         r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\tahoma.ttf"]


def pick_font(text, w, h):
    path = next((f for f in FONTS if os.path.exists(f)), None)
    if path is None:
        raise SystemExit("no usable TTF found")
    size = h + 4
    while size > 6:
        f = ImageFont.truetype(path, size)
        l, t, r, b = f.getbbox(text)
        if (r - l) <= w - 2 and (b - t) <= h - 2:
            return f, (r - l), (b - t), l, t
        size -= 1
    f = ImageFont.truetype(path, 7)
    l, t, r, b = f.getbbox(text)
    return f, (r - l), (b - t), l, t


def main():
    src, dst = sys.argv[1], sys.argv[2]
    preview = sys.argv[3] if len(sys.argv) > 3 else None
    d = bytearray(open(src, "rb").read())
    o = TIM_OFF
    tot, cs, isz, hs, cc, pf, mm, ct, it, w, h = struct.unpack_from("<IIIHHBBBBHH", d, o + 16)
    assert it == 4 and w == 256 and h == 256, (it, w, h)
    pix = o + 16 + hs

    def get(x, y):
        b = d[pix + y*(w//2) + x//2]
        return (b & 0xF) if x % 2 == 0 else (b >> 4)

    def put(x, y, v):
        i = pix + y*(w//2) + x//2
        if x % 2 == 0:
            d[i] = (d[i] & 0xF0) | (v & 0xF)
        else:
            d[i] = (d[i] & 0x0F) | ((v & 0xF) << 4)

    for (x0, y0, x1, y1, text) in LABELS:
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        # clear the rect
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                put(x, y, 0)
        font, tw, th, lx, ty = pick_font(text, bw, bh)
        mask = Image.new("L", (bw, bh), 0)
        dr = ImageDraw.Draw(mask)
        dr.text(((bw - tw)//2 - lx, (bh - th)//2 - ty), text, font=font, fill=255)
        m = mask.load()
        core = [[m[x, y] > 110 for x in range(bw)] for y in range(bh)]
        for y in range(bh):
            for x in range(bw):
                if core[y][x]:
                    put(x0 + x, y0 + y, FILL)
        # 1px outline around the glyphs
        for y in range(bh):
            for x in range(bw):
                if core[y][x]:
                    continue
                # 4-way (not 8-way) outline: keeps the glyphs from fattening up
                near = False
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < bh and 0 <= xx < bw and core[yy][xx]:
                        near = True; break
                if near:
                    put(x0 + x, y0 + y, OUTLINE)
        print("  %-13s -> rect %3d,%3d %3dx%-3d  font %dpx" % (text, x0, y0, bw, bh, font.size))

    open(dst, "wb").write(bytes(d))
    print("wrote %s (%d bytes, size unchanged: %s)"
          % (dst, len(d), len(d) == os.path.getsize(src)))

    if preview:
        clut = pix + isz
        pal = []
        for i in range(16):
            r, g, b, a = d[clut + i*4: clut + i*4 + 4]
            pal.append((r, g, b))
        img = Image.new("RGB", (w, h))
        p = img.load()
        for y in range(h):
            for x in range(w):
                p[x, y] = pal[get(x, y)]
        img.resize((w*2, h*2), Image.NEAREST).save(preview)
        print("preview -> %s" % preview)


if __name__ == "__main__":
    main()
