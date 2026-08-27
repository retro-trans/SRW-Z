# -*- coding: utf-8 -*-
"""Export the glyph atlas as an editable texture, and import an edited one back.

The atlas is 69 glyphs of 12x24 at 2 bits per pixel (4 shades), packed 3 bytes
per row, living at 0x78A5B0 in the cave segment. This lays it out as a 12x6 grid
of cells - 144x144 px at 1:1 - so it can be painted on in any pixel editor and
read straight back.

    font_texture.py <iso> --export [--out DIR]
    font_texture.py <iso> --import <png> [--write]

Rules for an edited texture:
  * keep it 144x144, one 12x24 cell per glyph, same grid order
  * greyscale; only FOUR values survive - they are snapped to 0/85/170/255
  * baseline is row 19 of each cell, descenders reach row 22
  * ink must stay inside the 12px cell width or it will be clipped
  * the pen advance is derived from each glyph's ink, so redraw narrower and the
    text automatically sets tighter - rerun patch_vwf_widths.py after importing

Glyph order: . " ' ! , - ? then 0-9, A-Z, a-z (left to right, top to bottom).
"""
import os
import sys

from PIL import Image

CAVE_VA, CAVE_FOFF = 0x78A070, 0x34D770
ELF_LBA, ELF_SIZE = 455, 3471624
ATLAS_VA, GB, ROWS, CELL_W, NART = 0x78A5B0, 72, 24, 12, 69
COLS = 12
LEVELS = [0, 85, 170, 255]
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + \
        list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))


def foff(va):
    return CAVE_FOFF + (va - CAVE_VA)


def read_elf(iso):
    f = open(iso, "rb")
    f.seek(ELF_LBA * 2048)
    elf = bytearray(f.read(ELF_SIZE))
    f.close()
    return elf


def export(iso, outdir):
    elf = read_elf(iso)
    raw = elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB]
    rows = (NART + COLS - 1) // COLS
    img = Image.new("L", (COLS * CELL_W, rows * ROWS), 0)
    px = img.load()
    for g in range(NART):
        cell = raw[g * GB:(g + 1) * GB]
        ox, oy = (g % COLS) * CELL_W, (g // COLS) * ROWS
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            for x in range(CELL_W):
                px[ox + x, oy + r] = LEVELS[(bits >> (22 - 2 * x)) & 3]
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    one = os.path.join(outdir, "font_texture_1x.png")
    img.save(one)
    big = img.resize((img.size[0] * 8, img.size[1] * 8), Image.NEAREST)
    big.save(os.path.join(outdir, "font_texture_8x.png"))
    print("wrote %s  (%dx%d, 1:1 - this is the editable one)"
          % (one, img.size[0], img.size[1]))
    print("wrote %s  (8x nearest, for viewing)"
          % os.path.join(outdir, "font_texture_8x.png"))
    print("grid: %d columns x %d rows of %dx%d cells, order . \" ' ! , - ? 0-9 A-Z a-z"
          % (COLS, rows, CELL_W, ROWS))


def load_png(path):
    img = Image.open(path).convert("L")
    rows = (NART + COLS - 1) // COLS
    want = (COLS * CELL_W, rows * ROWS)
    if img.size != want:
        raise SystemExit("texture must be %dx%d, got %dx%d"
                         % (want[0], want[1], img.size[0], img.size[1]))
    px = img.load()
    out = bytearray()
    changed = []
    for g in range(NART):
        ox, oy = (g % COLS) * CELL_W, (g // COLS) * ROWS
        for r in range(ROWS):
            bits = 0
            for x in range(CELL_W):
                v = px[ox + x, oy + r]
                lvl = min(range(4), key=lambda i: abs(LEVELS[i] - v))
                bits |= lvl << (22 - 2 * x)
            out += bytes([(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF])
    return bytes(out)


def import_(iso, png, write):
    elf = read_elf(iso)
    old = bytes(elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB])
    new = load_png(png)
    assert len(new) == NART * GB, len(new)
    diff = [g for g in range(NART)
            if old[g * GB:(g + 1) * GB] != new[g * GB:(g + 1) * GB]]
    print("glyphs changed: %d %s"
          % (len(diff), "".join(chr(CHARS[g]) for g in diff[:40])))
    if not diff:
        print("nothing to do")
        return
    if not write:
        print("\n(dry run - pass --write to apply)")
        return
    elf[foff(ATLAS_VA):foff(ATLAS_VA) + NART * GB] = new
    f = open(iso, "r+b")
    f.seek(ELF_LBA * 2048)
    f.write(bytes(elf))
    f.close()
    g = open(iso, "rb"); g.seek(ELF_LBA * 2048); back = g.read(ELF_SIZE); g.close()
    assert back == bytes(elf), "readback mismatch"
    print("written and verified")
    print("NOTE: rerun patch_vwf_widths.py (--revert then apply) so the advance "
          "table matches the new ink extents.")


def main():
    iso = sys.argv[1]
    if "--export" in sys.argv:
        outdir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv \
            else "analysis"
        export(iso, outdir)
    elif "--import" in sys.argv:
        png = sys.argv[sys.argv.index("--import") + 1]
        import_(iso, png, "--write" in sys.argv)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
