# -*- coding: utf-8 -*-
"""4x PCSX2 texture replacements for the intermission MENU buttons.

Unlike the gold bar labels, these are single-frame (no palette pulse):
one dump per button, all sharing palette hash b5d69c65ef990140. The
Japanese twins (機体系 / パイロット系 / 小隊編成 / バザー / オプション /
データ管理 / 次のマップへ / インターミッション) occupy the same slots
pre-patch and are listed too, so the pack also works on an unpatched
disc and survives a re-translated button.

Buttons are white text on transparent with a soft dark shadow; the HD
render reproduces that: Segoe UI Semibold (close to the original grotesk)
at 4x, white fill, 1px-equivalent dark outline, offset shadow.

Usage: gen_hd_menu.py [--dry]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

DUMPS = r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\dumps"
REPL = r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\replacements"
FONT = r"C:\Windows\Fonts\seguisb.ttf"          # Segoe UI Semibold
FONT_FALLBACK = r"C:\Windows\Fonts\segoeui.ttf"
SCALE = 4

# datahash -> label (verified from the dump contact sheets)
PIECES = {
    "97b1839c89631570": "Units",
    "aa1a9d2a6969d378": "Units",          # 機体系 (JP twin)
    "4e98da3e40168c5a": "Pilots",
    "28e98ea639b26964": "Pilots",         # パイロット系
    "cdaecb3e1d6db1a8": "Squads",
    "dff2123c42f05daa": "Squads",         # 小隊編成
    "cd496845f16b09fd": "Bazaar",
    "65f374195d8bc8cc": "Bazaar",         # バザー
    "2c1b2616595f222d": "Options",
    "ef0bb7078499984f": "Options",        # オプション
    "2f523e89088efeaf": "Data",
    "e133acc0d8e00fce": "Data",
    "53077f9311266f1c": "Data",           # データ管理
    "e39c8bf1e679fcba": "Data",           # データ管理
    "44411de339498dbd": "Next Map",
    "a12b747cb03dc1d2": "Next Map",       # 次のマップへ
    "1d0c05dccae56e50": "INTERMISSION",
    "e5d8ade1ffe6d900": "INTERMISSION",
    "ccae0b6261f47295": "INTERMISSION",   # インターミッション
    "8b21734257f264c4": "INTERMISSION",
}


def ink_bbox(im):
    px = im.load()
    xs, ys = [], []
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 40 and (r + g + b) > 100:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def load_font(pt):
    for p in (FONT, FONT_FALLBACK):
        try:
            return ImageFont.truetype(p, pt)
        except OSError:
            continue
    return ImageFont.load_default()


def render(text, dump):
    bbox = ink_bbox(dump)
    if bbox is None:
        return None
    W, H = dump.width * SCALE, dump.height * SCALE
    bx0, by0, bx1, by1 = [v * SCALE for v in bbox]
    bw, bh = bx1 - bx0, by1 - by0
    ss = 2
    stroke = max(1, SCALE * ss // 4)
    pt = bh * ss
    tmp = ImageDraw.Draw(Image.new("L", (8, 8)))
    while pt > 8:
        font = load_font(pt)
        bb = tmp.textbbox((0, 0), text, font=font, stroke_width=stroke)
        if bb[3] - bb[1] <= bh * ss:
            break
        pt -= 2
    bb = tmp.textbbox((0, 0), text, font=font, stroke_width=stroke)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    layer = Image.new("RGBA", (tw + 8 * ss, th + 8 * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    sh = SCALE * ss // 2
    dr.text((-bb[0] + sh, -bb[1] + sh), text, font=font,
            fill=(0, 20, 25, 190), stroke_width=stroke,
            stroke_fill=(0, 20, 25, 190))
    dr.text((-bb[0], -bb[1]), text, font=font,
            fill=(255, 255, 255, 255), stroke_width=stroke,
            stroke_fill=(20, 45, 55, 235))
    layer = layer.crop(layer.getbbox() or (0, 0, 1, 1))
    tw2 = min(layer.width, bw)
    layer = layer.resize((tw2, bh), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(layer, (bx0 + (bw - tw2) // 2, by0), layer)
    return out


def main():
    dry = "--dry" in sys.argv
    os.makedirs(REPL, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(DUMPS)):
        if not fn.endswith(".png"):
            continue
        label = PIECES.get(fn.split("-")[0])
        if not label:
            continue
        dump = Image.open(os.path.join(DUMPS, fn)).convert("RGBA")
        if dry:
            print("%-14s %s %s" % (label, dump.size, fn))
            n += 1
            continue
        hd = render(label, dump)
        if hd is None:
            print("SKIP (no ink):", fn)
            continue
        hd.save(os.path.join(REPL, fn))
        n += 1
    print("%s %d menu pieces" % ("classified" if dry else "generated", n))


if __name__ == "__main__":
    main()
