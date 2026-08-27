# -*- coding: utf-8 -*-
"""Build PCSX2 texture replacements for the LIBRARY menu.

The LIBRARY entries are art. The atlas in /DATA/JTIM.BIN that LOOKS like this
menu (image #5, the one with the OPTION title) is NOT what the screen draws -
patching it changed nothing in game. The real textures are these, captured from
a PCSX2 dump on the LIBRARY screen:

    8ed5786b95541a75-2cdd03b431356fe3-00002253            512x256
    8a344e380294371b-2cdd03b431356fe3-r257x257-00002213   257x257

Both share the palette hash 2cdd03b431356fe3. Unlike the dialogue font - which
is a DEMAND-DECODED cache page whose hash changes every scene, so replacement
can never match - these are static UI textures with one stable hash each, so a
replacement applies reliably. The pack is keyed by SERIAL, not CRC, so it works
on any build and any machine.

Pale label text on transparent, with a soft dark shadow. PS2 alpha is 0..128, so
"opaque" here is 128 and PCSX2 dumps/reloads on that scale - the replacement is
written back with the same alpha values sampled from the original, never 255.

English is drawn centred on each label's own centre, matching how the originals
sit, and clamped to the original box so nothing overruns into the NEW! badge.

Usage: make_library_replacement.py <dumpdir> <outdir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\arialbd.ttf"

# (x0, x1, y0, y1, english) - text boxes only, never the badge or the button
LABELS = [
    (32, 161, 34, 52, "Robot Data"),
    (22, 172, 74, 92, "Character Data"),
    (59, 133, 114, 132, "Glossary"),
    (23, 168, 155, 171, "Sound Select"),
    (23, 168, 195, 211, "Scenario Chart"),
    (54, 140, 234, 252, "Strategy Q&A"),
]
FILES = ["8ed5786b95541a75-2cdd03b431356fe3-00002253.png",
         "8a344e380294371b-2cdd03b431356fe3-r257x257-00002213.png"]


def sample(im, x0, x1, y0, y1):
    """Text and shadow colours, taken only from FULLY OPAQUE pixels.

    Sampling the brightest pixel regardless of alpha picks a half-transparent
    antialiased edge, and the replacement text then draws washed-out grey
    instead of the original's pale white."""
    px = im.load()
    amax = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            amax = max(amax, px[x, y][3])
    best, worst = None, None
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            r, g, b, a = px[x, y]
            if a < amax:
                continue
            l = r + g + b
            if best is None or l > best[0]:
                best = (l, (r, g, b, a))
            if worst is None or l < worst[0]:
                worst = (l, (r, g, b, a))
    return (best[1] if best else (255, 255, 255, amax or 128),
            worst[1] if worst else (0, 0, 0, amax or 128))


def fit(text, bw, bh):
    for pt in range(bh + 6, 5, -1):
        f = ImageFont.truetype(FONT, pt)
        im = Image.new("L", (bw * 4, bh * 4), 0)
        ImageDraw.Draw(im).text((6, 6), text, font=f, fill=255)
        bb = im.getbbox()
        if bb and bb[2] - bb[0] <= bw and bb[3] - bb[1] <= bh:
            return im.crop(bb)
    raise SystemExit("cannot fit %r in %dx%d" % (text, bw, bh))


def main():
    dumpdir, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for name in FILES:
        src = os.path.join(dumpdir, name)
        if not os.path.exists(src):
            print("missing %s - skipped" % name)
            continue
        im = Image.open(src).convert("RGBA")
        W, H = im.size
        px = im.load()
        done = 0
        for x0, x1, y0, y1, text in LABELS:
            if x1 >= W or y1 >= H:
                continue
            fg, sh = sample(im, x0, x1, y0, y1)
            # Erase with a MARGIN. The original text carries a soft halo a few
            # pixels beyond its own bounding box; clearing only the box leaves
            # that halo behind as a dotted rectangle around the new text.
            # 4px is safe: the labels end by x=172 and the NEW! badge starts at
            # x=190, and the rows are 20px apart.
            M = 4
            for y in range(max(0, y0 - M), min(H, y1 + M + 1)):
                for x in range(max(0, x0 - M), min(W, x1 + M + 1)):
                    px[x, y] = (0, 0, 0, 0)
            bw, bh = x1 - x0 + 1, y1 - y0 + 1
            m = fit(text, bw, bh)
            mw, mh = m.size
            ox = x0 + (bw - mw) // 2          # centred, as the originals are
            oy = y0 + (bh - mh) // 2
            mp = m.load()
            for j in range(mh):
                for i in range(mw):
                    if mp[i, j] < 96:
                        continue
                    X, Y = ox + i + 1, oy + j + 1
                    if x0 <= X <= x1 and y0 <= Y <= y1:
                        px[X, Y] = sh
            for j in range(mh):
                for i in range(mw):
                    v = mp[i, j]
                    if v < 40:
                        continue
                    X, Y = ox + i, oy + j
                    if not (x0 <= X <= x1 and y0 <= Y <= y1):
                        continue
                    if v >= 128:
                        px[X, Y] = fg
                    else:
                        px[X, Y] = (fg[0], fg[1], fg[2], max(1, fg[3] * v // 255))
            done += 1
        out = os.path.join(outdir, name)
        im.save(out)
        print("%-54s %dx%d  %d labels" % (name[:50], W, H, done))
    print("\nwrote to %s" % outdir)


if __name__ == "__main__":
    main()
