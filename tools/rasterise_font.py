# -*- coding: utf-8 -*-
"""Rasterise a TrueType face into the game's 12x24 half-width atlas format.

This is the same job gen_hwatlas.py does, but parameterised so candidate faces
can be compared before anything is built. Rendering is done large and
downscaled (supersampling) so edge pixels carry real partial coverage, then
quantised to the 4 levels the 2-bit packing allows.

Only JAPANESE faces are viable: the cell is 12px wide with an 18px cap height,
and a face's Latin has to be half-width (hankaku) to fit that. Measured on
Windows, MS Gothic / MS Mincho / BIZ UDGothic / UD Digi Kyokasho fit; Tahoma,
Verdana, Segoe UI, Meiryo and Yu Gothic are 9-11px too wide at that height.

  rasterise_font.py <font.ttc> [--cap 18] [--gap 1] [--bias 0] [--out a.bin] [--preview p.png]

The atlas is 69 glyphs x 72 bytes, order . " ' ! , - ? then 0-9 A-Z a-z, packed
3 bytes per row MSB-first, 24 rows, baseline on row 19.
"""
import sys

from PIL import Image, ImageDraw, ImageFont

CELL_W, ROWS, NART, GB = 12, 24, 69, 72
BASELINE = 19
SS = 8                      # supersample factor
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A)) + \
        list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))


def cap_size(path, cap):
    """Point size whose 'H' is `cap` pixels tall."""
    for pt in range(8, 80):
        f = ImageFont.truetype(path, pt)
        im = Image.new("L", (pt * 4, pt * 4), 0)
        ImageDraw.Draw(im).text((5, 5), "H", font=f, fill=255)
        bb = im.getbbox()
        if bb and (bb[3] - bb[1]) >= cap:
            return pt, f
    raise SystemExit("face never reaches cap height %d" % cap)


def quant(v, bias):
    """Map 0-255 coverage to the 4 stored levels.

    bias=0 is the neutral split at 64/128/192. Raising it lowers the thresholds
    so partially-covered pixels round UP - more fully-solid ink, less grey.
    That is the lever for weight: the game draws DARK text on a light box, so
    grey pixels cost contrast, and a face that measures 'soft' is usually just
    being quantised timidly rather than being genuinely thin."""
    t = [64 - bias, 128 - bias * 2, 192 - bias * 3]
    return 0 if v < t[0] else 1 if v < t[1] else 2 if v < t[2] else 3


def render(path, cap=18, gap=1, bias=0):
    pt, _ = cap_size(path, cap)
    big = ImageFont.truetype(path, pt * SS)
    out = []
    for code in CHARS:
        ch = chr(code)
        W, H = CELL_W * SS, ROWS * SS
        im = Image.new("L", (W * 2, H * 2), 0)
        d = ImageDraw.Draw(im)
        # draw with the glyph's baseline on BASELINE, left edge at `gap`
        d.text((gap * SS, BASELINE * SS), ch, font=big, fill=255, anchor="ls")
        im = im.crop((0, 0, W, H))
        small = im.resize((CELL_W, ROWS), Image.LANCZOS)
        p = small.load()
        out.append([[quant(p[x, y], bias) for x in range(CELL_W)]
                    for y in range(ROWS)])
    return out, pt


def pack(glyphs):
    b = bytearray()
    for px in glyphs:
        for r in range(ROWS):
            bits = 0
            for x in range(CELL_W):
                bits |= px[r][x] << (22 - 2 * x)
            b += bytes([(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF])
    assert len(b) == NART * GB
    return bytes(b)


def main():
    path = sys.argv[1]
    cap = int(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else 18
    gap = int(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 1
    bias = int(sys.argv[sys.argv.index("--bias") + 1]) if "--bias" in sys.argv else 0
    glyphs, pt = render(path, cap, gap, bias)
    print("%s at %dpt (cap %d) -> 69 glyphs" % (path, pt, cap))
    if "--out" in sys.argv:
        o = sys.argv[sys.argv.index("--out") + 1]
        open(o, "wb").write(pack(glyphs))
        print("wrote %s (%d bytes)" % (o, NART * GB))
    if "--preview" in sys.argv:
        p = sys.argv[sys.argv.index("--preview") + 1]
        S = 6
        cols = 12
        rows = (NART + cols - 1) // cols
        img = Image.new("RGB", (cols * (CELL_W * S + 6) + 8,
                                rows * (ROWS * S + 18) + 8), (18, 20, 26))
        d = ImageDraw.Draw(img)
        for i, px in enumerate(glyphs):
            gx = 8 + (i % cols) * (CELL_W * S + 6)
            gy = 8 + (i // cols) * (ROWS * S + 18)
            d.rectangle([gx, gy + 12, gx + CELL_W * S, gy + 12 + ROWS * S],
                        fill=(34, 38, 48))
            for r in range(ROWS):
                for c in range(CELL_W):
                    v = px[r][c]
                    if v:
                        lv = (0, 90, 175, 255)[v]
                        d.rectangle([gx + c * S, gy + 12 + r * S,
                                     gx + (c + 1) * S - 1, gy + 12 + (r + 1) * S - 1],
                                    fill=(lv, lv, lv))
            d.text((gx, gy), chr(CHARS[i]), fill=(150, 220, 150))
        img.save(p)
        print("wrote %s" % p)


if __name__ == "__main__":
    main()
