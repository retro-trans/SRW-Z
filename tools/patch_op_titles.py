# -*- coding: utf-8 -*-
"""Translate the OPENING's series-title cards (OP0/OP1/OP2.BIN).

These are not text anywhere on the disc - they are pixels: one 512x512
PSMT8 (8-bit indexed, PS2-swizzled) TIM2 per file, each holding 6-7 title
strips of ~35 rows.  Decoding needed three things to line up:
  - the TIM2 picture header puts width/height at +0x14, NOT +0x10;
  - PSMT8 data is SWIZZLED (the classic block/column/byte mapping below);
  - a 256-entry PS2 CLUT is stored in the tiled order
    0-7, 16-23, 8-15, 24-31 within each group of 32.
Palette in these textures: 0 = transparent, 23 = white fill, 22 = near
white, 6 = dark blue edge, 1 = faint blue glow - so English is drawn with
the SAME indices and the CLUT never has to change.

Everything is rewritten in place (same 512x512, same file size), so no
relocation and no header edits.

Usage: patch_op_titles.py <iso> [--preview DIR] [--revert]
"""
import os
import re
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 512
PIX = 0x10 + 16 + 48
SECTOR = 2048
FILES = {                      # name: (lba, size, [(band_top, band_bottom)])
    "OP0": (1312162, 266224),
    "OP1": (1312292, 265872),
    "OP2": (1312422, 266352),
}
PRISTINE = r"E:\Projects\SRW Z\_work\iso\srwz_alldlg.bin"

# One entry per ink band, top to bottom, as decoded from the Japanese art.
TITLES = {
    "OP0": ["Mobile Suit Gundam SEED DESTINY",
            "Mazinger Z",
            "Super Dimension Century Orguss",
            "Space Warrior Baldios",
            "Mobile Suit Zeta Gundam",
            "Invincible Steel Man Daitarn 3",
            "Genesis of Aquarion"],
    "OP1": ["THE Big O",
            "Great Mazinger",
            "Invincible Superman Zambot 3",
            "Combat Mecha Xabungle",
            "Mobile Suit Gundam: Char's Counterattack",
            "Overman King Gainer"],
    "OP2": ["Gravion",
            "UFO Robo Grendizer",
            "After War Gundam X",
            "Getter Robo G",
            "Space Emperor God Sigma",
            "Turn A Gundam",
            "Symphonic Psalms Eureka Seven"],
}

FONT = r"C:\Windows\Fonts\timesbd.ttf"      # serif bold, closest to the 明朝
FILL, NEAR, EDGE, GLOW, CLEAR = 23, 22, 6, 1, 0
LEFT_PAD = 6


def _swizzle_map():
    m = []
    for y in range(H):
        for x in range(W):
            block = (y & (~0xF)) * W + (x & (~0xF)) * 2
            swap = (((y + 2) >> 2) & 0x1) * 4
            ypos = (((y & (~3)) >> 1) + (y & 1)) & 0x7
            column = ypos * W * 2 + ((x + swap) & 0x7) * 4
            bsum = ((y >> 1) & 1) + ((x >> 2) & 2)
            m.append(block + column + bsum)
    return m


MAP = _swizzle_map()


def clut_order():
    idx = []
    for b in range(0, 256, 32):
        idx += list(range(b, b + 8)) + list(range(b + 16, b + 24)) + \
               list(range(b + 8, b + 16)) + list(range(b + 24, b + 32))
    return idx


def load(iso, name):
    lba, size = FILES[name]
    with open(iso, "rb") as f:
        f.seek(lba * SECTOR)
        d = f.read(size)
    px = d[PIX:PIX + W * H]
    plain = bytearray(W * H)
    for i, s in enumerate(MAP):
        plain[i] = px[s]
    cl = d[PIX + W * H:PIX + W * H + 1024]
    order = clut_order()
    pal = []
    for i in range(256):
        s = order[i] * 4
        r, g, b, a = cl[s:s + 4]
        pal.append((r, g, b, min(255, a * 2)))
    return d, plain, pal


def store(iso, name, plain):
    lba, size = FILES[name]
    with open(iso, "r+b") as f:
        f.seek(lba * SECTOR)
        d = bytearray(f.read(size))
        for i, s in enumerate(MAP):
            d[PIX + s] = plain[i]
        f.seek(lba * SECTOR)
        f.write(bytes(d))


def bands(plain):
    """[(top, bottom)] for every horizontal run of inked rows."""
    out, start = [], None
    for y in range(H):
        ink = any(plain[y * W + x] for x in range(W))
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            out.append((start, y - 1))
            start = None
    if start is not None:
        out.append((start, H - 1))
    return out


def draw_title(plain, top, bottom, text):
    """Blank the band, then paint `text` into it with the art's own indices."""
    height = bottom - top + 1
    for y in range(top, bottom + 1):
        for x in range(W):
            plain[y * W + x] = CLEAR
    K = 4                                   # supersample, then average
    size = height + 2
    while size > 8:
        font = ImageFont.truetype(FONT, size * K)
        img = Image.new("L", (W * K, height * K + 8 * K), 0)
        dr = ImageDraw.Draw(img)
        bb = dr.textbbox((0, 0), text, font=font)
        if bb[2] - bb[0] <= (W - LEFT_PAD * 2) * K:
            break
        size -= 1
    dr.text((LEFT_PAD * K - bb[0], (height * K - (bb[3] - bb[1])) // 2 - bb[1]),
            text, font=font, fill=255)
    small = img.resize((W, height + 8), Image.LANCZOS)
    p = small.load()
    for y in range(height):
        for x in range(W):
            v = p[x, y]
            if v >= 200:
                idx = FILL
            elif v >= 130:
                idx = NEAR
            elif v >= 60:
                idx = EDGE
            elif v >= 20:
                idx = GLOW
            else:
                continue
            plain[(top + y) * W + x] = idx
    return size


def main():
    iso = sys.argv[1]
    preview = None
    if "--preview" in sys.argv:
        preview = sys.argv[sys.argv.index("--preview") + 1]
    if "--revert" in sys.argv:
        for name in FILES:
            lba, size = FILES[name]
            with open(PRISTINE, "rb") as src:
                src.seek(lba * SECTOR)
                blob = src.read(size)
            with open(iso, "r+b") as f:
                f.seek(lba * SECTOR)
                f.write(blob)
            print("%s restored from the pristine image" % name)
        return
    for name in FILES:
        d, plain, pal = load(iso, name)
        bs = bands(plain)
        titles = TITLES[name]
        assert len(bs) == len(titles), \
            "%s: %d ink bands but %d titles" % (name, len(bs), len(titles))
        for (top, bot), text in zip(bs, titles):
            pt = draw_title(plain, top, bot, text)
            print("  %s y=%3d..%3d  %-42s (%dpx)" % (name, top, bot, text, pt))
        if preview:
            img = Image.new("RGB", (W, H))
            q = img.load()
            for y in range(H):
                for x in range(W):
                    r, g, b, a = pal[plain[y * W + x]]
                    q[x, y] = (r, g, b) if a else (0, 0, 0)
            img.save(os.path.join(preview, "%s_en.png" % name))
        else:
            store(iso, name, plain)
    print("preview written" if preview else "done")


if __name__ == "__main__":
    main()
