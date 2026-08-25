"""Generate a COMPACT 1bpp half-width glyph atlas (fits the ELF sector slack).

62 glyphs (0-9, A-Z, a-z), each a 12x16 cell, 1 bit/pixel, packed contiguously
(row-major within a glyph, glyphs in index order). 12*16/8 = 24 bytes/glyph ->
62*24 = 1488 bytes. Runtime code expands each to a 16x16 PSMCT32 cell in the
grid atlas (index i -> col i%16, row i//16) written to free EE RAM, then DMAs.

Outputs: font1.bin (raw 1bpp) and font1.png (preview).
Index map (must match the injector's code->index):
  0-9  '0'..'9' ; 10-35 'A'..'Z' ; 36-61 'a'..'z'
"""
import sys
from PIL import Image, ImageDraw, ImageFont

CW, CH = 12, 14   # cell (glyph) pixel size (row-aligned, 2 bytes/row -> 28 B/glyph)

def chars():
    return ([chr(c) for c in range(ord('0'), ord('9') + 1)] +
            [chr(c) for c in range(ord('A'), ord('Z') + 1)] +
            [chr(c) for c in range(ord('a'), ord('z') + 1)])

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else r'E:\Projects\SRW Z\_work\optx\font1'
    font = None
    for name, sz in [("consola.ttf", 15), ("arial.ttf", 14), ("cour.ttf", 15)]:
        try:
            font = ImageFont.truetype(name, sz); break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    cs = chars()
    # preview strip + 1bpp bytes
    prev = Image.new("L", (CW * len(cs), CH), 0)
    pd = ImageDraw.Draw(prev)
    data = bytearray()
    for i, ch in enumerate(cs):
        cell = Image.new("L", (CW, CH), 0)
        d = ImageDraw.Draw(cell)
        bb = d.textbbox((0, 0), ch, font=font)
        d.text((-bb[0] + 1, -bb[1] + 1), ch, font=font, fill=255)
        px = cell.load()
        for y in range(CH):
            bits = 0
            for x in range(CW):
                if px[x, y] > 110:
                    bits |= (1 << (7 - (x & 7)))
                if (x & 7) == 7 or x == CW - 1:
                    data.append(bits); bits = 0
        prev.paste(cell, (i * CW, 0))
    open(out + ".bin", "wb").write(bytes(data))
    prev.resize((prev.width * 3, prev.height * 3), Image.NEAREST).save(out + ".png")
    print("1bpp atlas: %d glyphs, %d bytes -> %s.bin (%d bytes/glyph)" %
          (len(cs), len(data), out, CH * ((CW + 7) // 8)))

if __name__ == "__main__":
    main()
