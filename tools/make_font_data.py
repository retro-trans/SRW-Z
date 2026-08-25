"""Generate half-width ASCII glyph data + index table for the VWF boot-hook.

For each mapped ASCII char, emits:
  - the JIS decoded-font-buffer index (empirically confirmed from 0x9AE610),
  - a 24x24 1bpp glyph (72 bytes, left-aligned, baseline ~19),
  - an advance width (for the later VWF advance patch).

Blob layout (little-endian), consumed by the hook in patch_font.py:
  u16 count
  count * { u16 index; u8 width; u8 pad; u8 glyph[72] }   (76 bytes/record)
"""
import struct
from PIL import ImageFont

FONT = "C:/Windows/Fonts/tahoma.ttf"
PX = 20
BASELINE = 19
LEFT = 1

# Confirmed indices in the decoded font buffer (0x9AE610), from idx_map.png:
#   digits 0-9 -> 207..216 ; A-Z -> 224..249 ; a-z -> 257..282
idx = {}
for i in range(10):
    idx[chr(0x30 + i)] = 207 + i
for i in range(26):
    idx[chr(0x41 + i)] = 224 + i
for i in range(26):
    idx[chr(0x61 + i)] = 257 + i

font = ImageFont.truetype(FONT, PX)
from PIL import Image, ImageDraw

records = []
for ch in sorted(idx, key=lambda c: idx[c]):
    im = Image.new("L", (24, 24), 0)
    d = ImageDraw.Draw(im)
    bb = font.getbbox(ch)
    lsb = bb[0] if bb else 0
    d.text((LEFT - lsb, BASELINE), ch, fill=255, font=font, anchor="ls")
    # advance width = ink width + 2 (space handled elsewhere)
    w = max(2, min(23, (bb[2] - bb[0]) + 2)) if bb else 8
    # pack 24x24 1bpp, MSB-first per row (bit x from left)
    px = im.load()
    glyph = bytearray(72)
    for y in range(24):
        for x in range(24):
            if px[x, y] >= 128:
                glyph[y * 3 + (x >> 3)] |= (0x80 >> (x & 7))
    records.append((idx[ch], w, bytes(glyph), ch))

blob = bytearray()
blob += struct.pack("<H", len(records))
for index, w, glyph, ch in records:
    blob += struct.pack("<HBB", index, w, 0) + glyph

with open("_work/font/font_data.bin", "wb") as f:
    f.write(blob)
print("records:", len(records), " blob bytes:", len(blob))
print("sample:", [(c, i, w) for (i, w, g, c) in records[:6]])
print("wrote _work/font/font_data.bin")
