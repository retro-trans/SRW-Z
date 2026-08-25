"""Half-width glyph atlas v5 - GRAYSCALE (2bpp, 4 alpha levels).

69 glyphs: . " ' ! , - ?  0-9  A-Z  a-z. Each 12x20 px, baseline row 16.
Rendered SUPERSAMPLED (4x: MS Gothic outline at 80px, no bitmap strike) and
LANCZOS-downscaled for real anti-aliased coverage, then quantized to 4 levels
(0/1/2/3 -> stamped as 4bpp nibbles 0/5/10/15, matching the game's own
antialiased master-font look). Packed 2 bits/px MSB-first: one row = 24 bits
= 3 bytes (w = sum lv[x] << (22-2x)); 20 rows = 60 B/glyph; 69*60 = 4140 B.
BOLD (menu) variants are NOT stored: the stamper dilates at stamp time.
"""
import sys
from PIL import Image, ImageFont, ImageDraw

CW, CH = 12, 20
BASELINE = 16
K = 4                       # supersample factor
STROKE = 2                  # ~0.5px weight at 1x
PUNCT = ['.', '"', "'", '!', ',', '-', '?']


def chars():
    return (PUNCT +
            [chr(c) for c in range(ord('0'), ord('9') + 1)] +
            [chr(c) for c in range(ord('A'), ord('Z') + 1)] +
            [chr(c) for c in range(ord('a'), ord('z') + 1)])


def load_font():
    for name in ["msgothic.ttc", "arial.ttf", "tahoma.ttf"]:
        try:
            return ImageFont.truetype(name, 20 * K)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else r'E:\Projects\SRW Z\_work\hwbuild\hwatlas'
    font = load_font()
    ascent, descent = font.getmetrics()
    cs = chars()
    data = bytearray()
    prev = Image.new("L", (CW * len(cs), CH), 0)
    for i, ch in enumerate(cs):
        big = Image.new("L", (CW * K, CH * K), 0)
        d = ImageDraw.Draw(big)
        bb = d.textbbox((0, 0), ch, font=font, stroke_width=STROKE)
        gw = bb[2] - bb[0]
        ox = (CW * K - gw) // 2 - bb[0]
        d.text((ox, BASELINE * K - ascent), ch, font=font, fill=255,
               stroke_width=STROKE, stroke_fill=255)
        cell = big.resize((CW, CH), Image.LANCZOS)
        px = cell.load()
        for y in range(CH):
            w = 0
            for x in range(CW):
                a = px[x, y]
                lv = 3 if a >= 170 else 2 if a >= 100 else 1 if a >= 40 else 0
                w |= lv << (22 - 2 * x)
                px[x, y] = lv * 85
            data += bytes([(w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF])
        prev.paste(cell, (i * CW, 0))
    open(out + ".bin", "wb").write(bytes(data))
    prev.resize((prev.width * 4, prev.height * 4), Image.NEAREST).save(out + ".png")
    print("hwatlas v5 grayscale: %d glyphs, %d bytes -> %s.bin" % (len(cs), len(data), out))


if __name__ == "__main__":
    main()
