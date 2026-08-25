"""Half-width atlas v6 - NATIVE GAME FONT.

Source: analysis/native_cells.bin = 69 fullwidth Latin/punct cells (24x24
4bpp, 288B each) ripped from the live master font at 0x9AE610 (demand-decoded
by displaying the full set via `variant165.py fontdump`, dumped over PINE).

Per glyph: ink column span located; wider than 12px -> the ink strip alone is
LANCZOS-resampled to 12px (grayscale, so stems stay smooth - unlike the old
binary squish); narrower -> centered unscaled. Rows are copied 1:1 (full
24-row window: baseline row ~21, quotes at the top and descenders at the
bottom all intact - the stamper writes all 24 rows, no clearing).

Quantized to 2bpp (levels 0/5/10/15 after the stamper's x5 expansion, nearest
match to the native 4bpp values). Packed 12px x 2b = 3B/row, 24 rows = 72B
per glyph, 69*72 = 4968 B. Bold menu variants are dilated at stamp time.

Output: hwatlas.bin + preview PNG. Order: . " ' ! , - ?  0-9  A-Z  a-z.
"""
import sys
from PIL import Image, ImageFilter

CW, ROWS = 12, 24
INK = 10        # target ink width: user pixel-count showed native S displays
                # ~0.8x our width at equal height (native glyphs fill ~13/24
                # of their box; 12/12 fill made ours read 25% wider)
THIN = 3        # MinFilter size at 4x supersample: 3 = ~0.5px stroke thinning
                # (compacting 15px ink into 12px keeps absolute stroke width,
                # which reads too heavy at half-width - thin to compensate)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else r'E:\Projects\SRW Z\_work\hwbuild\hwatlas'
    raw = open(r"E:\Projects\SRW Z\_work\analysis\native_cells.bin", "rb").read()
    n = len(raw) // 288
    data = bytearray()
    prev = Image.new("L", (CW * n, ROWS), 0)
    for ci in range(n):
        cell = raw[ci * 288:(ci + 1) * 288]
        img = Image.new("L", (24, ROWS), 0)
        px = img.load()
        for y in range(ROWS):
            for xb in range(12):
                b = cell[y * 12 + xb]
                px[xb * 2, y] = (b & 0xF) * 17
                px[xb * 2 + 1, y] = (b >> 4) * 17
        bb = img.getbbox()
        if bb is None:
            g = Image.new("L", (CW, ROWS), 0)
        else:
            x0, _, x1, _ = bb
            w = x1 - x0
            strip = img.crop((x0, 0, x1, ROWS))
            big = strip.resize((w * 4, ROWS * 4), Image.LANCZOS)
            binary = big.point(lambda a: 255 if a >= 96 else 0)
            thin = binary.filter(ImageFilter.MinFilter(THIN))
            tw = min(w, INK)
            gg = thin.resize((tw, ROWS), Image.LANCZOS)
            g = Image.new("L", (CW, ROWS), 0)
            g.paste(gg, ((CW - tw) // 2, 0))
        gp = g.load()
        for y in range(ROWS):
            w24 = 0
            for x in range(CW):
                a = gp[x, y]
                lv = 3 if a >= 150 else 2 if a >= 85 else 1 if a >= 35 else 0
                w24 |= lv << (22 - 2 * x)
                gp[x, y] = lv * 85
            data += bytes([(w24 >> 16) & 0xFF, (w24 >> 8) & 0xFF, w24 & 0xFF])
        prev.paste(g, (ci * CW, 0))
    open(out + ".bin", "wb").write(bytes(data))
    prev.resize((prev.width * 4, prev.height * 4), Image.NEAREST).save(out + ".png")
    print("hwatlas v6 NATIVE: %d glyphs, %d bytes -> %s.bin" % (n, len(data), out))


if __name__ == "__main__":
    main()
