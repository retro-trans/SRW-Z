# -*- coding: utf-8 -*-
"""Render a before/after demo of proportional spacing, from the SHIPPED glyphs.

The font is half-width but NOT proportional: patch_hwfont writes a constant 12
into the per-glyph width field (0x78a2ac `addiu t2,zero,0xc` -> `sh t2,0xc(s0)`),
and the advance hook at 0x78BA60 reads that field and adds 1, so every Latin
glyph advances exactly 13px. The field is per-glyph and the hook already honours
it - only the constant stands between this and real VWF.

This reads the 69 letterforms actually stamped into the master font (atlas at
0x78A5B0, 72 B/glyph, 24 rows of 12px 2bpp MSB-first) and draws three passes of
the same real dialogue lines:

  FIXED    every glyph advances 13px            (what ships today)
  TRIM-R   advance = ink right edge + 2         (safe: art unchanged, only the
                                                 dead space after a glyph goes)
  TRIM-LR  art shifted to its ink left edge,    (true VWF: needs the stamper to
           advance = ink width + 2               shift art, a bigger change)

Usage: vwf_demo.py <iso> [out.png]
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

CELL_W, ROWS, GB = 12, 24, 72
ATLAS_VA = 0x78A5B0
CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
NART = 69
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + \
        list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
FIXED_ADV = 13
GAP = 2
SPACE_ADV = 6

LINES = [
    u"...Touma, that duty is yours.",
    u"As you wish...",
    u"Can you manage it...?",
    u"If the Genesis Machine Gran",
    u"It will not repeat my mistakes!",
    u"Illiterate militia in Wisconsin",
]


def load_atlas(iso):
    f = open(iso, "rb")
    f.seek(455 * 2048)
    elf = f.read(3471624)
    f.close()
    base = CAVE_FOFF + (ATLAS_VA - CAVE_VA)
    raw = elf[base:base + NART * GB]
    glyphs = {}
    for g, code in enumerate(CHARS):
        cell = raw[g * GB:(g + 1) * GB]
        px = [[0] * CELL_W for _ in range(ROWS)]
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            if len(b) < 3:
                break
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            for x in range(CELL_W):
                px[r][x] = (bits >> (22 - 2 * x)) & 3
        cols = [x for x in range(CELL_W)
                if any(px[r][x] for r in range(ROWS))]
        left = cols[0] if cols else 0
        right = cols[-1] if cols else CELL_W - 1
        glyphs[chr(code)] = (px, left, right)
    return glyphs


def draw(img, x0, y0, px, left, shift, scale, colour):
    d = img.load()
    for r in range(ROWS):
        for c in range(CELL_W):
            v = px[r][c]
            if not v:
                continue
            lv = (85, 170, 255)[v - 1]
            X = x0 + (c - (left if shift else 0)) * scale
            Y = y0 + r * scale
            for dy in range(scale):
                for dx in range(scale):
                    if 0 <= X + dx < img.size[0] and 0 <= Y + dy < img.size[1]:
                        cur = d[X + dx, Y + dy]
                        val = int(lv * colour[0] / 255), int(lv * colour[1] / 255), int(lv * colour[2] / 255)
                        d[X + dx, Y + dy] = tuple(max(a, b) for a, b in zip(cur, val))


def render(img, lines, glyphs, mode, x0, y0, scale, colour):
    y = y0
    widths = []
    for ln in lines:
        x = x0
        for ch in ln:
            if ch == " ":
                x += SPACE_ADV * scale
                continue
            g = glyphs.get(ch)
            if g is None:                      # kagi etc: full-width block
                x += 24 * scale
                continue
            px, left, right = g
            if mode == "fixed":
                adv = FIXED_ADV
                draw(img, x, y, px, left, False, scale, colour)
            elif mode == "trimr":
                adv = right + GAP
                draw(img, x, y, px, left, False, scale, colour)
            else:
                adv = (right - left + 1) + GAP
                draw(img, x, y, px, left, True, scale, colour)
            x += adv * scale
        widths.append(x - x0)
        y += (ROWS + 4) * scale
    return widths


def main():
    iso = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "analysis/vwf_demo.png"
    glyphs = load_atlas(iso)
    scale = 2
    pad, lead = 20, 3
    modes = [("FIXED 13px  - ships today", "fixed", (245, 245, 245)),
             ("PROPORTIONAL - art unchanged", "trimr", (150, 235, 150)),
             ("PROPORTIONAL - art shifted", "trimlr", (150, 200, 255))]
    rowh = (ROWS + lead) * scale
    grouph = rowh * 3 + 14
    W = 1180
    H = pad * 2 + 30 + len(LINES) * grouph
    img = Image.new("RGB", (W, H), (14, 22, 34))
    d = ImageDraw.Draw(img)
    for i, (lab, _, col) in enumerate(modes):
        d.text((pad + i * 330, 8), lab, fill=col)
    stats = {m: [] for _, m, _ in modes}
    y = pad + 30
    for ln in LINES:
        for lab, mode, col in modes:
            w = render(img, [ln], glyphs, mode, pad, y, scale, col)[0]
            stats[mode].append(w)
            d.line([(pad + w, y), (pad + w, y + rowh - 6)], fill=(90, 105, 130))
            y += rowh
        d.line([(pad, y + 5), (W - pad, y + 5)], fill=(40, 52, 70))
        y += 14
    img.save(out)
    print("wrote %s (%dx%d)" % (out, W, H))
    f = sum(stats["fixed"])
    for mode in ("trimr", "trimlr"):
        m = sum(stats[mode])
        print("%-8s %.1f%% tighter than fixed" % (mode, 100.0 * (f - m) / f))

if __name__ == "__main__":
    main()
