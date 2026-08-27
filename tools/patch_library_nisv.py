# -*- coding: utf-8 -*-
"""Translate the LIBRARY menu in the ISO - the texture the game ACTUALLY draws.

0.8.94 repainted /DATA/JTIM.BIN image #5, which looks exactly like this menu but
is not what the screen blits, so nothing changed in game; the menu was then
translated with a PCSX2 texture replacement instead. That replacement is not
portable: PCSX2 dumped the page as 512x256 with no region field, so its hash
covers areas outside the art and build_texture_pack drops it as non-portable.
The standing rule is that a replacement which cannot apply on another machine is
not acceptable, so the art itself has to be patched.

Found by scanning the disc for the dump's own CLUT entries. The real texture is

    /DATA/NISVDATA.BIN   LBA 1568269, banlz record 0 (647,136 bytes plain)
    256x256, 8bpp, PSMT8-SWIZZLED
    pixels at 0x8c900, CLUT at 0x9c900 (the usual 0-7,16-23,8-15,24-31 tiling)

Confirmed by decoding it and matching the PCSX2 dump: 150 of 150 sampled pixels.
The 512x256 dump is the containing GS page, which is why no 512-wide layout ever
matched - the texture is 256 wide.

Read and write both go through the swizzle map, so the data is never deswizzled
and reswizzled - the same permutation is used in each direction.

The CLUT IS NEVER TOUCHED. English is painted with the art's own palette indices
sampled per row from the label being replaced, ranked by BRIGHTNESS rather than
by frequency: ranking by count picks the shadow on any row where the original
glyph had more shadow than fill, which drew dark bands through the letters.

All six labels are rendered at ONE point size - the largest that fits every one
of them - because sizing each to its own box makes the longer entries shrink and
the menu stops reading as a single menu.

Usage: patch_library_nisv.py <iso> [--preview PNG] [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from PIL import Image, ImageDraw, ImageFont

LBA, SIZE = 1568269, 555056
SECTOR = 2048
REC = 0
PIX, CLUT, W, H = 0x8c900, 0x9c900, 256, 256
FONT = r"C:\Windows\Fonts\arialbd.ttf"

# (y0, y1, english) - measured from the decoded texture; every label is 23px
# tall and centred on x=97, and the NEW! badge starts at x=185.
LABELS = [
    (32, 54, "Robot Data"),
    (72, 94, "Character Data"),
    (112, 134, "Glossary"),
    (152, 174, "Sound Select"),
    (192, 214, "Scenario Chart"),
    (232, 254, "Strategy Q&A"),
]
BOX_X0, BOX_X1 = 18, 177          # inside the widest original (20..175)
CENTRE = 97


def swizzle_map():
    m = []
    for y in range(H):
        for x in range(W):
            block = (y & (~0xF)) * W + (x & (~0xF)) * 2
            swap = (((y + 2) >> 2) & 1) * 4
            ypos = (((y & (~3)) >> 1) + (y & 1)) & 7
            m.append(block + ypos * W * 2 + ((x + swap) & 7) * 4
                     + ((y >> 1) & 1) + ((x >> 2) & 2))
    return m


MAP = swizzle_map()


def clut_order():
    o = []
    for b in range(0, 256, 32):
        o += list(range(b, b + 8)) + list(range(b + 16, b + 24)) + \
             list(range(b + 8, b + 16)) + list(range(b + 24, b + 32))
    return o


def palette(p):
    o = clut_order()
    return [tuple(p[CLUT + o[i] * 4:CLUT + o[i] * 4 + 4]) for i in range(256)]


def get(p, x, y):
    return p[PIX + MAP[y * W + x]]


def put(p, x, y, v):
    p[PIX + MAP[y * W + x]] = v


def ramp(p, pal, y0, y1):
    """Per-row palette indices ranked by brightness, plus the darkest (shadow)."""
    lum = lambda i: pal[i][0] * 2 + pal[i][1] * 3 + pal[i][2]
    out, dark, darkl = {}, None, 1e9
    for y in range(y0, y1 + 1):
        seen = set(get(p, x, y) for x in range(BOX_X0, BOX_X1 + 1)
                   if pal[get(p, x, y)][3] > 40)
        if not seen:
            continue
        out[y] = sorted(seen, key=lum, reverse=True)
        for i in out[y]:
            if lum(i) < darkl:
                darkl, dark = lum(i), i
    return out, dark


def common_size(bw, bh):
    """Largest point size at which EVERY label fits its box."""
    for pt in range(bh + 8, 5, -1):
        f = ImageFont.truetype(FONT, pt)
        ok = True
        for _y0, _y1, text in LABELS:
            im = Image.new("L", (bw * 3, bh * 4), 0)
            ImageDraw.Draw(im).text((6, 6), text, font=f, fill=255)
            bb = im.getbbox()
            if not bb or bb[2] - bb[0] > bw or bb[3] - bb[1] > bh:
                ok = False
                break
        if ok:
            return pt
    raise SystemExit("no point size fits every label")


def mask(text, pt, bw, bh):
    f = ImageFont.truetype(FONT, pt)
    im = Image.new("L", (bw * 3, bh * 4), 0)
    ImageDraw.Draw(im).text((6, 6), text, font=f, fill=255)
    return im.crop(im.getbbox())


def paint(p, pal, y0, y1, text, pt):
    r, shadow = ramp(p, pal, y0, y1)
    if not r:
        return
    bw, bh = BOX_X1 - BOX_X0 + 1, y1 - y0 + 1
    m = mask(text, pt, bw, bh)
    mw, mh = m.size
    ox, oy = CENTRE - mw // 2, y0 + max(0, (bh - mh) // 2)
    # the box's own transparent index, taken from a corner of the row; if that
    # corner happens to hold ink, fall back to the most transparent entry
    clear = get(p, BOX_X0, y0)
    if pal[clear][3] > 40:
        clear = min(range(256), key=lambda i: pal[i][3])
    for y in range(y0, y1 + 1):
        for x in range(BOX_X0, BOX_X1 + 1):
            put(p, x, y, clear)
    mp = m.load()
    for j in range(mh):
        for i in range(mw):
            if mp[i, j] < 100:
                continue
            X, Y = ox + i + 2, oy + j + 2
            if BOX_X0 <= X <= BOX_X1 and y0 <= Y <= y1:
                put(p, X, Y, shadow)
    for j in range(mh):
        for i in range(mw):
            v = mp[i, j]
            if v < 40:
                continue
            X, Y = ox + i, oy + j
            if not (BOX_X0 <= X <= BOX_X1 and y0 <= Y <= y1):
                continue
            row = r.get(Y) or r[min(r, key=lambda k: abs(k - Y))]
            fill = row[0]
            mid = row[min(len(row) - 1, max(1, len(row) // 3))] if len(row) > 1 else fill
            put(p, X, Y, fill if v >= 128 else mid)
    print("   %-16r rows %3d..%-3d  drawn %dx%d at x=%d" % (text, y0, y1, mw, mh, ox))


def preview(p, pal, out):
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = pal[get(p, x, y)]
            px[x, y] = (r, g, b, min(255, a * 2))
    im.save(out)
    print("wrote %s" % out)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    p = bytearray(items[REC][1])
    pal = palette(p)

    pt = common_size(BOX_X1 - BOX_X0 + 1, 21)
    print("common point size: %d" % pt)
    for y0, y1, text in LABELS:
        paint(p, pal, y0, y1, text, pt)

    if "--preview" in sys.argv:
        preview(p, pal, sys.argv[sys.argv.index("--preview") + 1])

    hdr = items[REC][0]
    nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
    blob = banlz.compress_record(bytes(p))
    if len(blob) > nxt - hdr:
        blob = banlz.compress_record_optimal(bytes(p))
    print("rec%d recompressed: %d bytes (slot %d)" % (REC, len(blob), nxt - hdr))
    if len(blob) > nxt - hdr:
        raise SystemExit("REFUSING: record grew past its slot")
    if not write:
        print("\n(dry run - pass --write to apply)")
        return
    raw[hdr:hdr + len(blob)] = blob
    for i in range(hdr + len(blob), nxt):
        raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    assert bytes(chk[REC][1]) == bytes(p), "readback mismatch"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified (file size unchanged, CLUT untouched)")


if __name__ == "__main__":
    main()
