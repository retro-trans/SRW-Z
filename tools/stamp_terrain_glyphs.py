# -*- coding: utf-8 -*-
"""Draw micro AIR/GND/SEA/SPC art into the terrain kanji font cells.

The terrain letters (空陸海宇) are FONT-RENDERED, so PCSX2 texture
replacement cannot reach them - but the decoded master font lives in RAM
as 24x24 4bpp cells (288 B, 12 B/row, LOW nibble = even x) and we already
stamp the half-width Latin set into it. Same trick, different cells: draw
a 3-letter word small enough to fit one kanji cell, the SRW-30 style the
user asked for.

  cell(code) = FONTBASE + ((lead-0x81)*192 + (trail-0x40)) * 288
  FONTBASE   = u32 at 0x0046E3A8 (the heap moves; never hardcode)

Cells are demand-decoded on first display, so a stamp can be overwritten;
for the live test that only matters if the game re-decodes mid-session.

Usage: stamp_terrain_glyphs.py [--revert] [--size N]
"""
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

from PIL import Image, ImageDraw, ImageFont
from pine_read import Pine

FONTPTR = 0x0046E3A8
CELL_BYTES = 288
ROW_BYTES = 12
FONT = r"C:\Windows\Fonts\arialbd.ttf"

# kanji -> 3-letter micro word
WORDS = {
    "\u7a7a": "AIR",   # sky
    "\u9678": "GND",   # land
    "\u6d77": "SEA",   # sea
    "\u5b87": "SPC",   # space
    "\u6c34": "WTR",   # water (move-type kanji, distinct from \u6d77 sea)
}


def cell_addr(base, ch):
    b = ch.encode("cp932")
    lead, trail = b[0], b[1]
    idx = (lead - 0x81) * 192 + (trail - 0x40)
    return base + idx * CELL_BYTES


def render_cell(word, px_h):
    """24x24 4bpp nibble map: word centered, baseline near the kanji baseline."""
    K = 4
    img = Image.new("L", (24 * K, 24 * K), 0)
    dr = ImageDraw.Draw(img)
    pt = px_h * K
    while pt > 4:
        font = ImageFont.truetype(FONT, pt)
        bb = dr.textbbox((0, 0), word, font=font)
        if bb[2] - bb[0] <= 22 * K:
            break
        pt -= K // 2 or 1
    bb = dr.textbbox((0, 0), word, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    # right-align (the kanji filled the cell and touched its rating letter)
    x = (23 * K) - tw - bb[0]
    y = (21 * K) - th - bb[1]          # baseline row 21 = the Latin baseline
    dr.text((x, y), word, font=font, fill=255)
    small = img.resize((24, 24), Image.LANCZOS)
    p = small.load()
    out = bytearray(CELL_BYTES)
    for row in range(24):
        for col in range(24):
            v = p[col, row]
            lv = 15 if v >= 150 else 10 if v >= 90 else 5 if v >= 40 else 0
            if not lv:
                continue
            off = row * ROW_BYTES + col // 2
            if col % 2 == 0:
                out[off] = (out[off] & 0xF0) | lv
            else:
                out[off] = (out[off] & 0x0F) | (lv << 4)
    return bytes(out)


def main():
    revert = "--revert" in sys.argv
    size = 13
    if "--size" in sys.argv:
        size = int(sys.argv[sys.argv.index("--size") + 1])
    p = Pine()
    base = p.read32_batch([FONTPTR])[0]
    print("master font base: %#x" % base)
    for ch, word in WORDS.items():
        a = cell_addr(base, ch)
        if revert:
            data = bytes(CELL_BYTES)          # blank; game re-decodes the kanji
        else:
            data = render_cell(word, size)
        for off in range(0, CELL_BYTES, 4):
            p.write32(a + off, int.from_bytes(data[off:off + 4], "little"))
        print("%s -> %-4s cell %#x" % (ch, "(blank)" if revert else word, a))
    print("done")


if __name__ == "__main__":
    main()
