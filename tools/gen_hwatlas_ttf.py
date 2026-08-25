# -*- coding: utf-8 -*-
"""Half-width glyph atlas (24-row / 72B-per-glyph format) from any TTF.

Matches the SHIPPED hwatlas.bin geometry (12x24 cells, 2bpp levels packed
3B/row, baseline ~row 20, cap height ~18px) so patch_hwfont / the live
stamper accept it unchanged. Wide fonts are horizontally condensed to the
cell; variable fonts get wdth=75 first, which condenses more gracefully.

Usage: gen_hwatlas_ttf.py <font.ttf> <out-prefix> [capheight_px]
"""
import sys

from PIL import Image, ImageDraw, ImageFont

CW, CH = 12, 24
BASELINE = 20
K = 4
PUNCT = ['.', '"', "'", '!', ',', '-', '?']


def chars():
    return (PUNCT +
            [chr(c) for c in range(ord('0'), ord('9') + 1)] +
            [chr(c) for c in range(ord('A'), ord('Z') + 1)] +
            [chr(c) for c in range(ord('a'), ord('z') + 1)])


def main():
    path, out = sys.argv[1], sys.argv[2]
    cap_target = int(sys.argv[3]) if len(sys.argv) > 3 else 17
    stroke = int(sys.argv[4]) if len(sys.argv) > 4 else K // 2
    # find pt size whose cap height ~= cap_target (at 1x)
    pt = cap_target * K
    font = None
    for _ in range(40):
        font = ImageFont.truetype(path, pt)
        try:
            font.set_variation_by_axes([75, 400])   # wdth, wght if variable
        except Exception:
            pass
        d = ImageDraw.Draw(Image.new("L", (8, 8)))
        bb = d.textbbox((0, 0), "H", font=font)
        cap = bb[3] - bb[1]
        if abs(cap - cap_target * K) <= K:
            break
        pt += K if cap < cap_target * K else -K
    ascent, descent = font.getmetrics()
    data = bytearray()
    prev = Image.new("L", (CW * 69, CH), 0)
    for i, ch in enumerate(chars()):
        big = Image.new("L", (CW * K * 4, CH * K), 0)
        d = ImageDraw.Draw(big)
        bb = d.textbbox((0, 0), ch, font=font, stroke_width=stroke)
        gw = max(1, bb[2] - bb[0])
        d.text((-bb[0], BASELINE * K - ascent), ch, font=font, fill=255,
                stroke_width=stroke, stroke_fill=255)
        ink = big.getbbox()
        if ink:
            gl = big.crop((ink[0], 0, ink[2], CH * K))
            tw = min(gl.width, (CW - 1) * K)
            gl = gl.resize((tw, CH * K), Image.LANCZOS)
            cell = Image.new("L", (CW * K, CH * K), 0)
            cell.paste(gl, ((CW * K - tw) // 2, 0))
        else:
            cell = Image.new("L", (CW * K, CH * K), 0)
        small = cell.resize((CW, CH), Image.LANCZOS)
        px = small.load()
        for y in range(CH):
            w = 0
            for x in range(CW):
                a = px[x, y]
                lv = 3 if a >= 150 else 2 if a >= 90 else 1 if a >= 40 else 0
                w |= lv << (22 - 2 * x)
                px[x, y] = lv * 85
            data += bytes([(w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF])
        prev.paste(small, (i * CW, 0))
    assert len(data) == 69 * 72, len(data)
    open(out + ".bin", "wb").write(bytes(data))
    prev.resize((prev.width * 3, prev.height * 3), Image.NEAREST).save(out + ".png")
    print("atlas: 69 glyphs, %d bytes, pt=%d -> %s.bin" % (len(data), pt // K, out))


if __name__ == "__main__":
    main()
