# -*- coding: utf-8 -*-
"""Illustrate what "rasterised from MS Gothic" means, stage by stage.

MS Gothic is a TrueType face: each letter is a mathematical OUTLINE, scalable to
any size. The PS2 has no outline renderer for our glyphs - the game's font is a
grid of pixels, 12x24 per cell at 2 bits each. Rasterising is the conversion.

tools/gen_hwatlas.py does it in four steps, reproduced here side by side:

  1. OUTLINE    MS Gothic drawn large (80px) - smooth, resolution-independent
  2. DOWNSCALE  LANCZOS to a 12px-wide cell - edge pixels get PARTIAL coverage,
                which is what antialiasing is
  3. QUANTISE   those 256 grey levels crushed to 4 (0/1/2/3), the most the
                2-bit-per-pixel packing can hold
  4. SHIPPED    the same glyph read back out of the built image, for comparison

Step 3 is why 'w', 'W' and 'm' look washed out: three vertical strokes have to
fit in a ~10px ink box, so the middle stroke lands between pixel columns, covers
roughly half of each, and quantises to a mid grey instead of solid white. Every
other letter has strokes that land on pixel boundaries.

Usage: explain_raster.py <iso> [out.png] [chars]
"""
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/msgothic.ttc"
BIG = 80
CELL_W, CELL_H = 12, 20
ROWS, GB, NART = 24, 72, 69
ATLAS_VA, CAVE_VA, CAVE_FOFF = 0x78A5B0, 0x78A070, 0x34D770
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + \
        list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
LEVELS = [0, 90, 175, 255]


def shipped(iso, ch):
    f = open(iso, "rb"); f.seek(455 * 2048); elf = f.read(3471624); f.close()
    g = CHARS.index(ord(ch))
    base = CAVE_FOFF + (ATLAS_VA - CAVE_VA) + g * GB
    cell = elf[base:base + GB]
    px = []
    for r in range(ROWS):
        b = cell[r * 3:r * 3 + 3]
        bits = (b[0] << 16) | (b[1] << 8) | b[2]
        px.append([(bits >> (22 - 2 * x)) & 3 for x in range(CELL_W)])
    return px


def stages(ch):
    fnt = ImageFont.truetype(FONT, BIG)
    big = Image.new("L", (BIG, int(BIG * 1.4)), 0)
    ImageDraw.Draw(big).text((BIG // 4, 0), ch, font=fnt, fill=255)
    bb = big.getbbox() or (0, 0, BIG, BIG)
    big = big.crop((bb[0], bb[1], bb[2], bb[3]))
    # Letterbox into the cell's aspect ratio instead of stretching. Without this
    # a narrow glyph like 'l' gets smeared to fill the width and the picture
    # lies about what the rasteriser is given.
    tw, th = CELL_W, CELL_H
    sc = min(float(tw) / big.size[0], float(th) / big.size[1])
    nw, nh = max(1, int(big.size[0] * sc)), max(1, int(big.size[1] * sc))
    small = Image.new("L", (tw, th), 0)
    small.paste(big.resize((nw, nh), Image.LANCZOS), ((tw - nw) // 2, th - nh))
    canvas = Image.new("L", (int(big.size[1] * tw / float(th)), big.size[1]), 0)
    canvas.paste(big, ((canvas.size[0] - big.size[0]) // 2, 0))
    big = canvas
    q = [[min(3, small.getpixel((x, y)) * 4 // 256) for x in range(CELL_W)]
         for y in range(CELL_H)]
    return big, small, q


def main():
    iso = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "analysis/raster_explained.png"
    chars = sys.argv[3] if len(sys.argv) > 3 else "wnl"
    S = 14
    colw = CELL_W * S + 30
    W = 40 + colw * 4
    H = 60 + len(chars) * (CELL_H * S + 40)
    img = Image.new("RGB", (W, H), (18, 20, 26))
    d = ImageDraw.Draw(img)
    heads = ["1. MS Gothic outline", "2. downscaled to 12px",
             "3. quantised to 4 levels", "4. shipped in the game"]
    for i, h in enumerate(heads):
        d.text((22 + i * colw, 12), h, fill=(190, 200, 215))
    d.text((22, 30), "grey = partial pixel coverage; that is what antialiasing is",
           fill=(120, 130, 145))

    y = 52
    for ch in chars:
        big, small, q = stages(ch)
        ship = shipped(iso, ch)
        # 1 outline
        b = big.resize((CELL_W * S, CELL_H * S), Image.LANCZOS)
        img.paste(b.convert("RGB"), (22, y))
        # 2 downscale (greyscale, nearest so pixels are visible)
        img.paste(small.resize((CELL_W * S, CELL_H * S), Image.NEAREST).convert("RGB"),
                  (22 + colw, y))
        # 3 quantised
        for r in range(CELL_H):
            for c in range(CELL_W):
                v = LEVELS[q[r][c]]
                d.rectangle([22 + 2 * colw + c * S, y + r * S,
                             22 + 2 * colw + (c + 1) * S - 1, y + (r + 1) * S - 1],
                            fill=(v, v, v))
        # 4 shipped
        for r in range(min(ROWS, CELL_H + 4)):
            for c in range(CELL_W):
                v = LEVELS[ship[r][c]]
                if v:
                    d.rectangle([22 + 3 * colw + c * S, y + (r - 2) * S,
                                 22 + 3 * colw + (c + 1) * S - 1,
                                 y + (r - 1) * S - 1], fill=(v, v, v))
        d.text((4, y + CELL_H * S // 2), ch, fill=(150, 220, 150))
        y += CELL_H * S + 40
    img.save(out)
    print("wrote %s (%dx%d)" % (out, W, H))


if __name__ == "__main__":
    main()
