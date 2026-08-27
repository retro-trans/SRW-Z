# -*- coding: utf-8 -*-
"""Build a 16-LEVEL glyph atlas (4bpp) for the half-width font.

WHY. The engine's master font is 4bpp - sixteen alpha levels - and the game's
own japanese glyphs use all 16 (measured from RAM at the font base held in BSS
global 0x0046E3A8). Our Latin atlas stores 2bpp, FOUR levels, and the stamper
expands them as level*5 -> 0/5/10/15. That quantisation is what makes the edges
look stepped; it is not a resolution limit.

FORMAT. 4bpp at 12px is 6 bytes per row, so a fixed 24-row atlas would need
69*144 = 9936 bytes and the cave only has 8995. Rows are therefore stored
VARIABLY - mean inked height is 16.7 of 24 - behind a small index:

    index   69 x u16   byte offset of each glyph's record, from ATLAS base
    record  u8 top     first inked row (0..23)
            u8 height  number of rows stored
            height x 6 bytes, 4bpp, LOW nibble = even x (matches the master
                       font's own packing, so the stamper is a straight copy)

Total for the current art: index 138 B + records 7032 B = 7170 B, ~1800 spare.

The stamper must clear the destination cell first (it already does) because
rows outside [top, top+height) are simply not written.

Usage:
  build_atlas16.py --from-font <ttf> [--cap 18] [--gap 1] [--bias 0] --out a16.bin
  build_atlas16.py --from-atlas <2bpp.bin> --out a16.bin      (upconvert, for A/B)
  build_atlas16.py --verify <a16.bin>
"""
import struct
import sys

CELL_W, ROWS, NART = 12, 24, 69
BASELINE, SS = 19, 8
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A)) + \
        list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))


def from_font(path, cap, gap, bias):
    from PIL import Image, ImageDraw, ImageFont
    for pt in range(8, 80):
        f = ImageFont.truetype(path, pt)
        im = Image.new("L", (pt * 4, pt * 4), 0)
        ImageDraw.Draw(im).text((5, 5), "H", font=f, fill=255)
        bb = im.getbbox()
        if bb and (bb[3] - bb[1]) >= cap:
            break
    big = ImageFont.truetype(path, pt * SS)
    out = []
    for code in CHARS:
        im = Image.new("L", (CELL_W * SS * 2, ROWS * SS * 2), 0)
        ImageDraw.Draw(im).text((gap * SS, BASELINE * SS), chr(code),
                                font=big, fill=255, anchor="ls")
        im = im.crop((0, 0, CELL_W * SS, ROWS * SS)).resize((CELL_W, ROWS),
                                                            Image.LANCZOS)
        p = im.load()
        rows = []
        for y in range(ROWS):
            rows.append([min(15, max(0, int(round((p[x, y] + bias) / 255.0 * 15))))
                         for x in range(CELL_W)])
        out.append(rows)
    return out, pt


def from_atlas2(path):
    """Upconvert the shipped 2bpp atlas, so the ONLY variable in an A/B test is
    the level count - level*5 is exactly what the current stamper produces."""
    raw = open(path, "rb").read()
    assert len(raw) == NART * 72, len(raw)
    out = []
    for g in range(NART):
        cell = raw[g * 72:(g + 1) * 72]
        rows = []
        for r in range(ROWS):
            b = cell[r * 3:r * 3 + 3]
            bits = (b[0] << 16) | (b[1] << 8) | b[2]
            rows.append([((bits >> (22 - 2 * x)) & 3) * 5 for x in range(CELL_W)])
        out.append(rows)
    return out, None


def pack(glyphs):
    recs, index, blob = [], [], bytearray()
    for rows in glyphs:
        inked = [r for r in range(ROWS) if any(rows[r])]
        if inked:
            top, h = inked[0], inked[-1] - inked[0] + 1
        else:
            top, h = 0, 0
        rec = bytearray([top, h])
        for r in range(top, top + h):
            for x in range(0, CELL_W, 2):
                rec.append((rows[r][x] & 0xF) | ((rows[r][x + 1] & 0xF) << 4))
        recs.append(bytes(rec))
    off = 2 * NART
    for rec in recs:
        index.append(off)
        off += len(rec)
    out = bytearray()
    for o in index:
        out += struct.pack("<H", o)
    for rec in recs:
        out += rec
    return bytes(out)


def unpack(blob):
    """Reference decoder - the Python model the MIPS must reproduce."""
    out = []
    for g in range(NART):
        off = struct.unpack_from("<H", blob, g * 2)[0]
        top, h = blob[off], blob[off + 1]
        rows = [[0] * CELL_W for _ in range(ROWS)]
        p = off + 2
        for r in range(top, top + h):
            for x in range(0, CELL_W, 2):
                b = blob[p]
                p += 1
                rows[r][x] = b & 0xF
                rows[r][x + 1] = b >> 4
        out.append(rows)
    return out


def main():
    if "--verify" in sys.argv:
        blob = open(sys.argv[sys.argv.index("--verify") + 1], "rb").read()
        gl = unpack(blob)
        lv = set(v for rows in gl for r in rows for v in r)
        heights = []
        for g in range(NART):
            off = struct.unpack_from("<H", blob, g * 2)[0]
            heights.append(blob[off + 1])
        print("atlas %d bytes, %d glyphs, levels used %d (%s..%s), height %d..%d"
              % (len(blob), NART, len(lv), min(lv), max(lv),
                 min(heights), max(heights)))
        return
    bias = int(sys.argv[sys.argv.index("--bias") + 1]) if "--bias" in sys.argv else 0
    cap = int(sys.argv[sys.argv.index("--cap") + 1]) if "--cap" in sys.argv else 18
    gap = int(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 1
    if "--from-font" in sys.argv:
        gl, pt = from_font(sys.argv[sys.argv.index("--from-font") + 1], cap, gap, bias)
        print("rendered at %dpt (cap %d, bias %d)" % (pt, cap, bias))
    else:
        gl, _ = from_atlas2(sys.argv[sys.argv.index("--from-atlas") + 1])
        print("upconverted from the shipped 2bpp atlas (level*5)")
    blob = pack(gl)
    back = unpack(blob)
    assert back == gl, "pack/unpack round-trip failed"
    print("packed %d bytes (index %d + records %d), round-trip OK"
          % (len(blob), 2 * NART, len(blob) - 2 * NART))
    if len(blob) > 8995:
        print("WARNING: %d bytes exceeds the cave budget of 8995" % len(blob))
    if "--out" in sys.argv:
        o = sys.argv[sys.argv.index("--out") + 1]
        open(o, "wb").write(blob)
        print("wrote %s" % o)


if __name__ == "__main__":
    main()
