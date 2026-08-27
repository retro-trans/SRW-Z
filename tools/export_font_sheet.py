# -*- coding: utf-8 -*-
"""Export the half-width Latin font actually stamped into the game.

The letterforms are NOT hand-drawn. tools/gen_hwatlas.py rasterises them from a
system TrueType face (MS Gothic, rendered at 80px and supersampled 4x, then
LANCZOS-downscaled and quantised to 4 alpha levels to match the game font's own
antialiased look), packs them 12x20 at 2 bits/pixel, and patch_hwfont stamps
them into the decoded master font in RAM at every setText.

This reads the 69 glyphs back out of the SHIPPED image so what you see is what
the game draws - atlas at 0x78A5B0, 72 B/glyph, 24 rows of 12px 2bpp MSB-first.

Usage: export_font_sheet.py <iso> [out.png] [--scale N]
"""
import sys

from PIL import Image, ImageDraw

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ATLAS_VA, GB, ROWS, CELL_W, NART = 0x78A5B0, 72, 24, 12, 69
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + \
        list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
LEVELS = [0, 90, 175, 255]


def load(iso):
    f = open(iso, "rb")
    f.seek(455 * 2048)
    elf = f.read(3471624)
    f.close()
    base = CAVE_FOFF + (ATLAS_VA - CAVE_VA)
    raw = elf[base:base + NART * GB]
    out = []
    for g in range(NART):
        cell = raw[g * GB:(g + 1) * GB]
        px = []
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            px.append([(bits >> (22 - 2 * x)) & 3 for x in range(CELL_W)])
        cols = [x for x in range(CELL_W) if any(px[r][x] for r in range(ROWS))]
        out.append((chr(CHARS[g]), px,
                    cols[0] if cols else 0, cols[-1] if cols else CELL_W - 1))
    return out


def main():
    iso = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") \
        else "analysis/font_sheet.png"
    scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 6
    glyphs = load(iso)

    per = 12
    cw, ch = CELL_W * scale + 18, ROWS * scale + 26
    rows = (len(glyphs) + per - 1) // per
    W, H = per * cw + 20, rows * ch + 40
    img = Image.new("RGB", (W, H), (18, 20, 26))
    d = ImageDraw.Draw(img)
    d.text((10, 8), "SRW Z half-width Latin font, read back from the shipped image "
                    "(12x24 cell, 2bpp).  label = char, number = pen advance px",
           fill=(200, 205, 215))

    for i, (chr_, px, left, right) in enumerate(glyphs):
        gx = 10 + (i % per) * cw
        gy = 30 + (i // per) * ch
        # cell background so the 12px box and the ink extents are visible
        d.rectangle([gx, gy + 14, gx + CELL_W * scale, gy + 14 + ROWS * scale],
                    fill=(34, 38, 48))
        adv = right + 2
        # shade the columns the advance actually consumes
        d.rectangle([gx, gy + 14, gx + adv * scale, gy + 14 + ROWS * scale],
                    fill=(46, 54, 70))
        for r in range(ROWS):
            for c in range(CELL_W):
                v = px[r][c]
                if v:
                    lv = LEVELS[v]
                    d.rectangle([gx + c * scale, gy + 14 + r * scale,
                                 gx + (c + 1) * scale - 1, gy + 14 + (r + 1) * scale - 1],
                                fill=(lv, lv, lv))
        d.text((gx, gy), "%s  %d" % (chr_, adv), fill=(150, 220, 150))
    img.save(out)
    print("wrote %s (%dx%d)" % (out, W, H))

    print("\nadvance by character:")
    for chr_, px, left, right in sorted(glyphs, key=lambda t: t[3] - t[2]):
        print("   %r ink %2d..%-2d width %2d advance %2d"
              % (chr_, left, right, right - left + 1, right + 2))


if __name__ == "__main__":
    main()
