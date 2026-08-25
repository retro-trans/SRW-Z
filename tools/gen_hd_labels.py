# -*- coding: utf-8 -*-
"""Generate 4x PCSX2 texture replacements for the intermission bar labels.

The GS uploads each label as its own small composited texture, one dump
file per gold-pulse frame (<datahash>-<palettehash>-rWxH-<group>.png).
For every dump hand-classified below we emit a same-named 4x PNG in
replacements/: the label re-rendered in crisp Georgia Bold, colorized
from that specific dump (pulse animation preserved), placed exactly on
the dump's ink bounding box (screen position unchanged).

Marquee/ticker pieces and the title card are deliberately NOT replaced
(user decisions). Obsolete-era pieces (harvested caps, JP labels) are
skipped - their data never renders on current builds.

Usage: gen_hd_labels.py [--dry]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

DUMPS = r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\dumps"
REPL = r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\replacements"
FONT = r"C:\Windows\Fonts\georgiab.ttf"
SCALE = 4

# hand-verified from the dump contact sheets (analysis/pieces_p*.png)
PIECES = {
    "EP": ["456177e047786edf", "55f45b1006f8ff81", "5763dae8ebc766a0",
           "99a3db218db48dd", "9a4a986c1aba0486", "b719d6d72a869989",
           "c2e4d70f964db42f", "d476e9ab029f0757", "dbb670a017032ca1",
           "e130d60bbd876c99"],
    "Ep": ["9414fac31d3867e7", "ab59172565abe332", "bfee6d9196e272f2",
           "d132ec01ac7544bc", "d7126f76b40815f0", "781318ddb14d98c",
           "e0ce3e54ed434f8", "4aa28249728085b1"],
    "SR Points": ["19e08d0e2cf9673b", "3c3c301ca7e12e36", "455de10eb456a72b",
                  "508d5ff906509165", "5ebf23c2d5f672b1", "6aa651f4cdd959a2",
                  "925f6ec8d211ae6d", "9a6bd8d8115b277d", "a34d8b65310c76f5",
                  "abcabd4e1d934c5a", "af022c87c60daf70", "c752e79de939ffe0",
                  "d0997e95287baf4d", "e4afb5456d1e89be"],
    "Funds": ["54e5321e2e929c5", "671a36c58e380e84", "7e882f8822b1eeb",
              "a3cbbabc7ac3d4c4", "a5394fd151a15ac4", "b07833c6816a2701",
              "cfa126c4ebc3b41c", "f8759f0023f8c388", "f8d35945cd65c435",
              "ff1e8b472b6d4b0b", "4436aa9208049ef3"],
    "BS.": ["542eeb6fa420bfec", "5541e5541042d9fa", "59b6bf732e4ec178",
            "633648b32ee8562a", "82f4be6e39dd97da", "9bb5b2b35279ea75",
            "a377f234881e5a0", "a565e4e5ea1f1c2d", "ebbb0114684f2f89",
            "eed029315d4c2bdd", "f1a3a1ab4ccb49d1"],
}
HASH2TEXT = {h: t for t, hs in PIECES.items() for h in hs}


def ink_bbox_and_colors(im):
    px = im.load()
    xs, ys = [], []
    cols = {}
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 60 and (r + g + b) > 40:
                xs.append(x)
                ys.append(y)
                cols[(r, g, b)] = cols.get((r, g, b), 0) + 1
    if not xs:
        return None, None
    bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    ranked = sorted(cols, key=lambda c: -sum(c))
    fill = ranked[0]
    edge = ranked[min(len(ranked) - 1, len(ranked) * 3 // 4)]
    shadow = ranked[-1]
    return bbox, (fill, edge, shadow)


def render_hd(text, dump):
    """Replacement image at 4x, glyphs on the dump's ink bbox."""
    bbox, colors = ink_bbox_and_colors(dump)
    if bbox is None:
        return None
    fill, edge, shadow = colors
    W, H = dump.width * SCALE, dump.height * SCALE
    bx0, by0, bx1, by1 = [v * SCALE for v in bbox]
    bw, bh = bx1 - bx0, by1 - by0
    ss = 2
    stroke = SCALE * ss // 3
    # find pt whose total ink height (incl stroke) fits bh
    pt = bh * ss
    tmp = Image.new("L", (8, 8))
    tdr = ImageDraw.Draw(tmp)
    while pt > 8:
        font = ImageFont.truetype(FONT, pt)
        bb = tdr.textbbox((0, 0), text, font=font, stroke_width=stroke)
        if bb[3] - bb[1] <= bh * ss:
            break
        pt -= 2
    bb = tdr.textbbox((0, 0), text, font=font, stroke_width=stroke)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    layer = Image.new("RGBA", (tw + 8 * ss, th + 8 * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    sh = SCALE * ss // 2
    dr.text((-bb[0] + sh, -bb[1] + sh), text, font=font,
            fill=shadow + (235,), stroke_width=stroke,
            stroke_fill=shadow + (235,))
    dr.text((-bb[0], -bb[1]), text, font=font,
            fill=fill + (255,), stroke_width=stroke,
            stroke_fill=edge + (255,))
    layer = layer.crop(layer.getbbox() or (0, 0, 1, 1))
    # squeeze/stretch horizontally onto the bbox, keep height
    layer = layer.resize((bw, bh), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(layer, (bx0, by0), layer)
    return out


def main():
    dry = "--dry" in sys.argv
    os.makedirs(REPL, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(DUMPS)):
        if not fn.endswith(".png"):
            continue
        dh = fn.split("-")[0]
        text = HASH2TEXT.get(dh)
        if not text:
            continue
        dump = Image.open(os.path.join(DUMPS, fn)).convert("RGBA")
        if dry:
            print("%-10s %s %s" % (text, dump.size, fn))
            n += 1
            continue
        hd = render_hd(text, dump)
        if hd is None:
            print("SKIP (no ink):", fn)
            continue
        hd.save(os.path.join(REPL, fn))
        n += 1
    print("%s %d pieces" % ("classified" if dry else "generated", n))


if __name__ == "__main__":
    main()
