"""Generate a half-width ASCII glyph atlas + width table for the SRW Z VWF patch.

Renders ASCII 0x20..0x7E from a TrueType font, antialiased, quantized to 4bpp
(16 levels — matches the game font's 4bpp format and gives smooth edges like the
Z2 translation). Packs them into a fixed-cell grid atlas and emits a per-glyph
advance-width table for proportional spacing.

Outputs:
  ascii_font.4bpp   raw 4bpp atlas, CELL_W*COLS x CELL_H*ROWS, row-major nibbles
  ascii_widths.bin  95 bytes, advance width (px) for each char 0x20..0x7E
  ascii_font_preview.png  visual check (upscaled, grid + widths)
"""
import sys, os
from PIL import Image, ImageFont, ImageDraw

FONT = sys.argv[1] if len(sys.argv) > 1 else "C:/Windows/Fonts/tahoma.ttf"
PXSIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 14
OUTDIR = sys.argv[3] if len(sys.argv) > 3 else "_work/font"

CELL_W, CELL_H = 16, 16      # matches ~16px atlas cell period measured in VRAM
COLS, ROWS = 16, 6           # 96 cells >= 95 glyphs
BASELINE = 13                # y of text baseline within the cell
LEFT_BEARING = 1

os.makedirs(OUTDIR, exist_ok=True)
font = ImageFont.truetype(FONT, PXSIZE)

chars = [chr(c) for c in range(0x20, 0x7F)]   # 95 glyphs
atlas = Image.new("L", (CELL_W * COLS, CELL_H * ROWS), 0)
draw = ImageDraw.Draw(atlas)
widths = []

for i, ch in enumerate(chars):
    col, row = i % COLS, i // COLS
    ox, oy = col * CELL_W, row * CELL_H
    # advance width from the font metrics
    adv = font.getlength(ch)
    if ch == " ":
        w = 4
    else:
        # ink bbox to compute a tight advance
        bbox = font.getbbox(ch)
        inkw = (bbox[2] - bbox[0]) if bbox else int(adv)
        w = max(2, min(CELL_W - 1, inkw + 2))
    widths.append(w)
    # draw glyph left-aligned in the cell at the baseline
    # PIL draws from top; anchor "ls" = left-baseline
    bbox = font.getbbox(ch)
    lsb = bbox[0] if bbox else 0
    draw.text((ox + LEFT_BEARING - lsb, oy + BASELINE), ch, fill=255, font=font, anchor="ls")

# quantize to 4bpp and pack row-major (low nibble = left pixel)
W, H = atlas.size
px = atlas.load()
packed = bytearray(W * H // 2)
for y in range(H):
    for x in range(0, W, 2):
        lo = px[x, y] >> 4
        hi = px[x + 1, y] >> 4
        packed[(y * W + x) // 2] = (hi << 4) | lo

with open(os.path.join(OUTDIR, "ascii_font.4bpp"), "wb") as f:
    f.write(packed)
with open(os.path.join(OUTDIR, "ascii_widths.bin"), "wb") as f:
    f.write(bytes(widths))

# preview: upscale 4x, draw cell grid + width markers
scale = 6
prev = atlas.resize((W * scale, H * scale), Image.NEAREST).convert("RGB")
pd = ImageDraw.Draw(prev)
for i, ch in enumerate(chars):
    col, row = i % COLS, i // COLS
    x0, y0 = col * CELL_W * scale, row * CELL_H * scale
    pd.rectangle([x0, y0, x0 + CELL_W * scale - 1, y0 + CELL_H * scale - 1], outline=(0, 80, 0))
    # advance width line (red)
    wx = x0 + widths[i] * scale
    pd.line([wx, y0, wx, y0 + CELL_H * scale - 1], fill=(255, 0, 0))
prev.save(os.path.join(OUTDIR, "ascii_font_preview.png"))

print("atlas %dx%d 4bpp -> %d bytes" % (W, H, len(packed)))
print("widths:", " ".join("%s=%d" % (repr(c), w) for c, w in zip(chars[:20], widths[:20])), "...")
print("avg width %.1f  (fullwidth cell would be %d)" % (sum(widths) / len(widths), CELL_W))
print("wrote %s/{ascii_font.4bpp,ascii_widths.bin,ascii_font_preview.png}" % OUTDIR)
