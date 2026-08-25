"""Author a half-width Latin glyph atlas (32-bit RGBA) for injection.

Layout: 16x16-px cells, 16 cells per row.
  index:  0-9   = digits '0'..'9'
         10-35  = 'A'..'Z'
         36-61  = 'a'..'z'
         62     = space (blank)
Atlas = 256 x 64 (16 cols x 4 rows). Glyphs rendered ~11px wide, left+baseline
aligned so a 12px dest cell tiles cleanly. Stored white (RGB=255) with
alpha=coverage, plus a raw .bin (linear RGBA, row-major) for ELF embedding.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

CELL = 16
COLS = 16
ROWS = 4
W, H = CELL * COLS, CELL * ROWS

def glyph_index(ch):
    if '0' <= ch <= '9':
        return ord(ch) - ord('0')
    if 'A' <= ch <= 'Z':
        return 10 + ord(ch) - ord('A')
    if 'a' <= ch <= 'z':
        return 36 + ord(ch) - ord('a')
    if ch == ' ':
        return 62
    raise ValueError(ch)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else r'E:\Projects\SRW Z\_work\optx\font12'
    # a thin, clean sans; fall back to default if unavailable
    font = None
    for name, sz in [("consola.ttf", 15), ("arial.ttf", 14), ("DejaVuSans.ttf", 13)]:
        try:
            font = ImageFont.truetype(name, sz); break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    im = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    chars = [chr(c) for c in range(ord('0'), ord('9') + 1)] + \
            [chr(c) for c in range(ord('A'), ord('Z') + 1)] + \
            [chr(c) for c in range(ord('a'), ord('z') + 1)]
    for ch in chars:
        idx = glyph_index(ch)
        cx = (idx % COLS) * CELL
        cy = (idx // COLS) * CELL
        # render white glyph; measure to left/baseline align within ~11px
        bb = d.textbbox((0, 0), ch, font=font)
        gw = bb[2] - bb[0]
        # scale down if wider than 11px so it stays half-width
        ox = cx - bb[0] + 1
        oy = cy - bb[1] + 1
        d.text((ox, oy), ch, font=font, fill=(255, 255, 255, 255))
    im.save(out + ".png")
    # raw linear RGBA
    with open(out + ".bin", "wb") as f:
        f.write(im.tobytes())
    print("atlas %dx%d written: %s.png / .bin (%d bytes)" % (W, H, out, W * H * 4))

if __name__ == "__main__":
    main()
