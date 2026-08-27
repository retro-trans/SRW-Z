# -*- coding: utf-8 -*-
"""Render sample text with a candidate font sheet next to the shipped one.

The only question that matters for a 12px font is what it looks like at 12px.
A candidate is downscaled into the 12x24 cell grid and quantised to the 4 shades
the format allows - exactly what shipping it would do - and drawn beside the
current glyphs at 1:1 and magnified.

Usage: try_font.py <iso> <candidate.png> [out.png]
"""
import sys
from PIL import Image, ImageDraw

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ATLAS_VA, GB, ROWS, CW, NART = 0x78A5B0, 72, 24, 12, 69
COLS = 12
LEVELS = [0, 85, 170, 255]
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A)) + \
        list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
IDX = {chr(c): i for i, c in enumerate(CHARS)}
LINES = ["Illiterate militia in Wisconsin",
         "Lord Shiruha, Lord Goushi,",
         "Touma won't run off. Why?"]


def shipped(iso):
    f = open(iso, "rb"); f.seek(455 * 2048); elf = f.read(3471624); f.close()
    base = CAVE_FOFF + (ATLAS_VA - CAVE_VA)
    raw = elf[base:base + NART * GB]
    out = []
    for g in range(NART):
        cell = raw[g * GB:(g + 1) * GB]
        px = []
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            px.append([(bits >> (22 - 2 * x)) & 3 for x in range(CW)])
        out.append(px)
    return out


def candidate(path, mode="quantise"):
    """mode 'quantise' averages down and keeps 4 shades; 'threshold' snaps each
    target pixel to solid or empty at 50% coverage. Averaging is right when the
    source grid matches the target; when it does not (this candidate draws on an
    ~11px grid where 8.71px is needed) every edge lands half-covered and the
    text comes out pale, so thresholding recovers the weight."""
    im = Image.open(path).convert("L")
    W, H = im.size
    cw, chh = W / float(COLS), H / 6.0
    out = []
    for g in range(NART):
        c, r = g % COLS, g // COLS
        box = im.crop((int(c * cw), int(r * chh), int((c + 1) * cw), int((r + 1) * chh)))
        small = box.resize((CW, ROWS), Image.LANCZOS)
        p = small.load()
        if mode == "threshold":
            out.append([[3 if p[x, y] >= 110 else 0 for x in range(CW)]
                        for y in range(ROWS)])
        else:
            out.append([[min(3, p[x, y] * 4 // 256) for x in range(CW)]
                        for y in range(ROWS)])
    return out


def draw_line(img, d, glyphs, text, x0, y0, s, col):
    x = x0
    for chr_ in text:
        if chr_ == " ":
            x += 6 * s
            continue
        g = IDX.get(chr_)
        if g is None:
            x += 12 * s
            continue
        px = glyphs[g]
        cols = [c for c in range(CW) if any(px[r][c] for r in range(ROWS))]
        adv = (cols[-1] + 2) if cols else CW
        for r in range(ROWS):
            for c in range(CW):
                v = px[r][c]
                if v:
                    lv = LEVELS[v]
                    d.rectangle([x + c * s, y0 + r * s,
                                 x + (c + 1) * s - 1, y0 + (r + 1) * s - 1],
                                fill=(int(lv * col[0] / 255), int(lv * col[1] / 255),
                                      int(lv * col[2] / 255)))
        x += adv * s
    return x - x0


def main():
    iso, cand = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "analysis/font_try.png"
    A = shipped(iso)
    B = candidate(cand, "quantise")
    C = candidate(cand, "threshold")
    sets = [("SHIPPED (MS Gothic rasterised)", A, (245, 245, 245)),
            ("CANDIDATE averaged down", B, (150, 235, 150)),
            ("CANDIDATE thresholded", C, (150, 200, 255))]
    W, H = 1000, 60 + len(LINES) * 2 * (ROWS * 3 + 16) + 120
    img = Image.new("RGB", (W, H), (16, 18, 24))
    d = ImageDraw.Draw(img)
    y = 40
    d.text((16, 12), "same text, both fonts, at 3x and then 1:1", fill=(190, 200, 215))
    for text in LINES:
        for name, gl, col in sets:
            d.text((16, y - 12), name, fill=col)
            draw_line(img, d, gl, text, 16, y, 3, col)
            y += ROWS * 3 + 16
        y += 10
    d.text((16, y), "actual size (1:1):", fill=(190, 200, 215))
    y += 16
    for name, gl, col in sets:
        draw_line(img, d, gl, LINES[0], 16, y, 1, col)
        draw_line(img, d, gl, LINES[2], 300, y, 1, col)
        y += ROWS + 8
    img.save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
