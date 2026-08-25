# -*- coding: utf-8 -*-
"""Paint the intermission/ticker JP kanji textures in English.

SUPERSEDED for the three bar labels by tools/harvest_labels.py (glyphs
harvested from the game's own p04 serif art, per user request) - run
harvest_labels.py iso AFTER this tool in any rebuild.

The intermission status bar and episode ticker are TEXTURE ART in
KVMDATA.BIN, same word-sheet format as the bazaar buttons: 4bpp 256x256
TIM2 pages, glyphs drawn with CLUT indices 15=fill, 11=edge, 4=shadow,
0=clear (palette-animated at runtime, so indices - not colors - matter).

Pages (file offset of TIM2 header inside KVMDATA.BIN, LBA 1289810):
  0x28B40 "p05": bazaar sheet - also holds bar labels 第 / BS．/ 資金．/
                 ＳＲポイント．(BS. is already Latin, kept)
  0x52070 "p10": ticker sheet - 第 話 「 」 までクリア！ / NEXT. 出撃 小隊

The 第N話 display everywhere (intermission bar, episode ticker, and the
chapter TITLE CARD's 第５話 line - the RAM strip "0123456789第話" is
composited from these glyphs plus the serif digits on page 6) is built
from these cells, so painting them translates all of it at once:
  第 -> "Ep"   話 -> blank   までクリア！ -> "cleared!"
  資金． -> "Funds"   ＳＲポイント． -> "SR Points"
  出撃 -> "Sortie"   小隊 -> "Squad"

First run saves the original JP cell bytes to analysis/kvm_labels_jp.bin
for --revert. Idempotent: cells already painted are skipped.

Usage: patch_intermission_labels.py <iso> [--revert]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WORK = r"E:\Projects\SRW Z\_work"
KVMDATA_LBA = 1289810
SECTOR = 2048
ROWBYTES = 128
FILL, EDGE, SHADOW, CLEAR = 15, 11, 4, 0
FONT = r"C:\Windows\Fonts\georgiab.ttf"
JPSAVE = os.path.join(WORK, "analysis", "kvm_labels_jp.bin")

# (page tex offset, x0, y0, x1, y1, text or "" to blank)
# p10 ticker cells REVERTED to JP 2026-08-20 (user: EN marquee can't look
# good in these cells - rollback). Only the p05 status-bar labels ship EN.
# kvm_labels_jp.bin still holds all 8 original blocks (p05 x3 then p10 x5).
CELLS = [
    (0x28B40, 143,  2, 166, 30, "EP"),
    (0x28B40, 209,  0, 255, 32, "Funds"),
    (0x28B40, 149, 40, 235, 63, "SR Points"),
]


def render_cell(text, w, h, style=None):
    from intermission_hotpatch import render_cell as v2
    return v2(text, w, h, style)


def _render_cell_v1_unused(text, w, h):
    """Index map in the sheet's glyph style (shadow +1,+1 at small sizes)."""
    out = [CLEAR] * (w * h)
    if not text:
        return out
    big = 4
    size = (h - 2) * big
    img = Image.new("L", (w * big, h * big), 0)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, size)
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    while tw > (w - 2) * big and size > 6 * big:
        size -= big
        font = ImageFont.truetype(FONT, size)
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = (w * big - tw) // 2 - bb[0]
    y = (h * big - th) // 2 - bb[1]
    draw.text((x, y), text, fill=255, font=font)
    small = img.resize((w, h), Image.LANCZOS)
    a = small.load()
    sh = 1 if h <= 20 else 2
    for yy in range(h):
        for xx in range(w):
            if a[xx, yy] >= 128 and xx + sh < w and yy + sh < h:
                out[(yy + sh) * w + (xx + sh)] = SHADOW
    for yy in range(h):
        for xx in range(w):
            v = a[xx, yy]
            if v >= 128:
                out[yy * w + xx] = FILL
            elif v >= 48 and out[yy * w + xx] == CLEAR:
                out[yy * w + xx] = EDGE
    return out


def cell_bytes(iso, texoff, x0, y0, x1, y1):
    """Read the packed 4bpp bytes covering the cell, row by row."""
    pixbase = KVMDATA_LBA * SECTOR + texoff + 16 + 48
    bx0, bx1 = x0 // 2, (x1 + 1) // 2
    rows = []
    for y in range(y0, y1):
        iso.seek(pixbase + y * ROWBYTES + bx0)
        rows.append(iso.read(bx1 - bx0))
    return b"".join(rows)


def write_cell(iso, texoff, x0, y0, x1, y1, idx):
    pixbase = KVMDATA_LBA * SECTOR + texoff + 16 + 48
    w = x1 - x0
    assert x0 % 2 == 0, "cell must start on even x"
    for yy, y in enumerate(range(y0, y1)):
        row = bytearray()
        for xb in range(0, w, 2):
            lo = idx[yy * w + xb]
            hi = idx[yy * w + xb + 1] if xb + 1 < w else CLEAR
            row.append(lo | (hi << 4))
        iso.seek(pixbase + y * ROWBYTES + x0 // 2)
        iso.write(bytes(row))


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    iso = open(iso_path, "r+b")
    saved = open(JPSAVE, "rb").read() if os.path.exists(JPSAVE) else None
    blocks = []
    pos = 0
    for texoff, x0, y0, x1, y1, text in CELLS:
        if x0 % 2:
            x0 -= 1
        cur = cell_bytes(iso, texoff, x0, y0, x1, y1)
        blocks.append((texoff, x0, y0, x1, y1, text, cur, pos))
        pos += len(cur)
    if revert:
        assert saved is not None, "no saved JP block to revert to"
        for texoff, x0, y0, x1, y1, text, cur, off in blocks:
            jp = saved[off:off + len(cur)]
            pixbase = KVMDATA_LBA * SECTOR + texoff + 16 + 48
            for yy, y in enumerate(range(y0, y1)):
                n = (x1 + 1) // 2 - x0 // 2
                iso.seek(pixbase + y * ROWBYTES + x0 // 2)
                iso.write(jp[yy * n:(yy + 1) * n])
            print("reverted %#x cell (%d,%d)" % (texoff, x0, y0))
        iso.close()
        return
    if saved is None:
        open(JPSAVE, "wb").write(b"".join(b[6] for b in blocks))
        print("saved JP originals -> %s" % JPSAVE)
    for texoff, x0, y0, x1, y1, text, cur, off in blocks:
        jp = saved[off:off + len(cur)] if saved else cur
        if saved and cur != jp:
            print("cell %#x (%d,%d) already painted, skip" % (texoff, x0, y0))
            continue
        w, h = x1 - x0, y1 - y0
        idx = render_cell(text, w, h)
        write_cell(iso, texoff, x0, y0, x1, y1, idx)
        print("painted %#x (%d,%d,%d,%d) -> %r" % (texoff, x0, y0, x1, y1, text))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
