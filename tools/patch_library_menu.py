# -*- coding: utf-8 -*-
"""Translate the LIBRARY menu, which is ART rather than text.

The six entries are not text anywhere on the disc - searching the whole 3.7GB
image for ロボット大図鑑 / サウンドセレクト / シナリオチャート / 用語事典 returns
nothing, and neither does every banlz archive. They are pixels in

    /DATA/JTIM.BIN  LBA 1568664, image #5 at file offset 0x394150
    512x256, 8bpp palettised, 256-colour CLUT, stored LINEARLY (not swizzled -
    tim2_dump reads it row-major and the result is correct)

Each entry appears TWICE, identical but for colour: a yellow copy (selected) on
the left, right-aligned to x=189, and a teal copy (normal) right-aligned to
x=389. Both are redrawn.

The CLUT IS NEVER TOUCHED. English is painted with the art's own palette
indices, sampled per row from the label being replaced, so the vertical gradient
and drop shadow come out of the original artwork rather than being invented:

    yellow  46 (240,248,136) at the top ... 62 (224,200,0) at the bottom
    teal    87 (128,152,248) ............... 85 (104,160,232)
    shadow  33 / 65  (0,0,8)

Text is fitted INSIDE the original bounding box and right-aligned to the same
edge, because the game blits each entry from its own UV rect - drawing wider
would be clipped.

Usage: patch_library_menu.py <iso> [--preview PNG] [--write] [--revert]
"""
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

LBA, SIZE = 1568664, 7539728
TIM = 0x394150
SECTOR = 2048
FONT = r"C:\Windows\Fonts\arialbd.ttf"

# (top, bottom, left_x0, left_x1, right_x0, right_x1, english)
ENTRIES = [
    (1,   35, 221, 333, 349, 461, "Strategy Q&A"),
    (41,  75,  31, 189, 231, 389, "Robot Data"),
    (78, 114,   4, 189, 204, 389, "Character Data"),
    (118, 154, 95, 189, 295, 389, "Glossary"),
    (157, 194, 12, 189, 212, 389, "Sound Select"),
    (199, 234, 10, 189, 210, 389, "Scenario Chart"),
]


def load(iso):
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    d = bytearray(f.read(SIZE))
    f.close()
    ho = TIM + 16
    tot, cs, isz, hs, cc, pf, mm, ct, it, w, h = struct.unpack_from(
        "<IIIHHBBBBHH", d, ho)
    assert it == 5 and w == 512 and h == 256, (it, w, h)
    return d, ho + hs, w, h


def ramp(d, pix, w, top, bot, x0, x1, pal):
    """Per-row (fill, mid) indices sampled from the label being replaced.

    Ranked by BRIGHTNESS, not by how often the index occurs. Ranking by count
    picks the SHADOW on any row where the original glyph happened to have more
    shadow than fill, which drew dark bands straight through the new letters.
    """
    out = {}
    dark, darkl = None, 1e9
    for y in range(top, bot + 1):
        seen = set(d[pix + y * w + x] for x in range(x0, x1 + 1)
                   if d[pix + y * w + x])
        if not seen:
            continue
        lum = lambda i: pal[i][0] * 2 + pal[i][1] * 3 + pal[i][2]
        ranked = sorted(seen, key=lum, reverse=True)
        out[y] = ranked
        for i in ranked:
            if lum(i) < darkl:
                darkl, dark = lum(i), i
    return out, dark


def palette(d, pix, isz):
    clut = pix + isz
    o = []
    for b in range(0, 256, 32):
        o += list(range(b, b + 8)) + list(range(b + 16, b + 24)) +              list(range(b + 8, b + 16)) + list(range(b + 24, b + 32))
    return [(d[clut + o[i] * 4], d[clut + o[i] * 4 + 1],
             d[clut + o[i] * 4 + 2], d[clut + o[i] * 4 + 3]) for i in range(256)]


def render(text, bw, bh):
    """Largest Arial Bold that fits the box; returns an L-mode coverage mask."""
    best = None
    for pt in range(bh + 8, 6, -1):
        f = ImageFont.truetype(FONT, pt)
        im = Image.new("L", (bw * 3, bh * 3), 0)
        ImageDraw.Draw(im).text((4, 4), text, font=f, fill=255)
        bb = im.getbbox()
        if bb and (bb[2] - bb[0]) <= bw - 2 and (bb[3] - bb[1]) <= bh - 4:
            best = im.crop(bb)
            break
    if best is None:
        raise SystemExit("cannot fit %r in %dx%d" % (text, bw, bh))
    return best


def paint(d, pix, w, top, bot, x0, x1, text, verbose, pal):
    ranked, shadow = ramp(d, pix, w, top, bot, x0, x1, pal)
    if not ranked:
        return
    bw, bh = x1 - x0 + 1, bot - top + 1
    mask = render(text, bw, bh)
    mw, mh = mask.size
    ox = x1 - mw                      # right-aligned, as the original is
    oy = top + max(0, (bh - mh) // 2)
    for y in range(top, bot + 1):
        for x in range(x0, x1 + 1):
            d[pix + y * w + x] = 0
    m = mask.load()
    # shadow first, offset down-right like the original
    for j in range(mh):
        for i in range(mw):
            if m[i, j] < 100:
                continue
            X, Y = ox + i + 2, oy + j + 2
            if x0 <= X <= x1 and top <= Y <= bot:
                d[pix + Y * w + X] = shadow
    for j in range(mh):
        for i in range(mw):
            v = m[i, j]
            if v < 40:
                continue
            X, Y = ox + i, oy + j
            if not (x0 <= X <= x1 and top <= Y <= bot):
                continue
            r = ranked.get(Y) or ranked.get(min(ranked, key=lambda k: abs(k - Y)))
            fill = r[0]
            # a genuine mid-tone for the antialiased edge: about a third of the
            # way down the row's brightness ranking, never the shadow
            mid = r[min(len(r) - 1, max(1, len(r) // 3))] if len(r) > 1 else fill
            d[pix + Y * w + X] = fill if v >= 128 else mid
    if verbose:
        print("   %-16r box %3d..%-3d rows %3d..%-3d  drawn %dx%d at x=%d"
              % (text, x0, x1, top, bot, mw, mh, ox))


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    d, pix, w, h = load(iso)
    orig = bytes(d[pix:pix + w * h])
    isz = struct.unpack_from("<I", d, TIM + 16 + 8)[0]
    pal = palette(d, pix, isz)

    for top, bot, lx0, lx1, rx0, rx1, text in ENTRIES:
        paint(d, pix, w, top, bot, lx0, lx1, text, True, pal)
        paint(d, pix, w, top, bot, rx0, rx1, text, False, pal)

    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ho = TIM + 16
        tot, cs, isz, hs, cc = struct.unpack_from("<IIIHH", d, ho)
        clut = pix + isz
        o = []
        for b in range(0, 256, 32):
            o += list(range(b, b + 8)) + list(range(b + 16, b + 24)) + \
                 list(range(b + 8, b + 16)) + list(range(b + 24, b + 32))
        pal = []
        for i in range(256):
            s = clut + o[i] * 4
            pal.append((d[s], d[s + 1], d[s + 2], min(255, d[s + 3] * 2)))
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            for x in range(w):
                px[x, y] = pal[d[pix + y * w + x]]
        img.save(out)
        print("wrote %s" % out)

    changed = sum(1 for i in range(w * h) if orig[i] != d[pix + i])
    print("index bytes changed: %d of %d" % (changed, w * h))
    if not write:
        print("\n(dry run - pass --write to apply)")
        return
    f = open(iso, "r+b")
    f.seek(LBA * SECTOR)
    f.write(bytes(d))
    f.close()
    g = open(iso, "rb"); g.seek(LBA * SECTOR); back = g.read(SIZE); g.close()
    assert back == bytes(d), "readback mismatch"
    print("written and verified (file size unchanged, CLUT untouched)")


if __name__ == "__main__":
    main()
