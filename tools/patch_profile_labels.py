# -*- coding: utf-8 -*-
"""Paint English over the pilot-profile labels on the KVMDATA word sheet.

姓名 / 愛称 / 決定 / 誕生日 / 血液型 / 名称変更 are TEXTURE ART, not strings -
they are not in the ELF, STAGE, COMPDATA or any other extracted file, because
they are glyphs on the same 4bpp TIM2 word sheet as the bazaar buttons
(KVMDATA.BIN + 0x28B40, 256x256). patch_bazaar_buttons.py paints the same
sheet; this paints the block below it.

    THE WIDTH IS FIXED BY WHAT IS NEXT TO THE LABEL.

Each label is right-aligned at x=254 and a checkerboard sprite sits immediately
to its left, so the game cannot be blitting anything wider than the glyphs
themselves - the checkerboard would show through. That gives a hard budget:
36px for the two-kanji labels, 54px for three, 72px for four, all 22 rows.
English has to fit inside it, which is why these read BORN and ALIAS rather
than BIRTHDAY and NICKNAME.

Boxes are measured from the art, not hardcoded: scan left from x=255 until six
blank columns, which separates the right-aligned label from the checkerboard.

Palette indices, not colours - 15 fill, 11 edge, 4 shadow, 0 clear - so the
runtime palette animation keeps working.

Usage: patch_profile_labels.py <iso> [--revert] [--preview-only]
Idempotent: saves the JP block once and refuses to overwrite its own backup.
"""
import hashlib
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

KVMDATA_LBA = 1289810
TEX_OFF_IN_FILE = 0x28B40
SECTOR = 2048
ROWBYTES = 128
FILL, EDGE, SHADOW, CLEAR = 15, 11, 4, 0
FONT = r"C:\Windows\Fonts\georgiab.ttf"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(ROOT, "analysis", "profile", "jp_labels_block.bin")
PREVIEW = os.path.join(ROOT, "analysis", "profile", "preview_labels.png")

BLOCK_Y0, BLOCK_Y1 = 113, 255            # the rows this tool owns
# (row0, row1, japanese, english, glyph count)
BANDS = [(113, 134, u"姓名", "NAME", 2),
         (137, 158, u"愛称", "ALIAS", 2),
         (161, 182, u"決定", "OK", 2),
         (185, 206, u"誕生日", "BORN", 3),
         (209, 230, u"血液型", "BLOOD", 3),
         (233, 254, u"名称変更", "RENAME", 4)]


def unpack(block, y0):
    """block (rows BLOCK_Y0..) -> 2d index grid for rows y0..y0+21."""
    g = []
    for y in range(y0, y0 + 22):
        r = block[(y - BLOCK_Y0) * ROWBYTES:(y - BLOCK_Y0 + 1) * ROWBYTES]
        row = []
        for b in r:
            row.append(b & 15)
            row.append(b >> 4)
        g.append(row)
    return g


PITCH, RIGHT = 18, 254           # kanji advance, and the right edge
MINRUN = 10          # a label stroke run; checkerboard runs are 6
MAXPT = 15           # cap, so the labels stay one visual size


def measure(g, nkanji):
    """Box for a right-aligned label: the trailing ink run on the row.

    Derived from the art, not hardcoded, but NOT by "scan left until N blank
    columns" either - the checkerboard sprite beside these labels is 6px
    squares separated by 2px gaps, so that scan walks straight through it and
    returns the whole row. What separates them is run LENGTH: every label run
    is at least 15 columns, every checkerboard run is exactly 6.

    So: take the rightmost run, absorb any neighbour that is close (<=2px, the
    gap inside a kanji) and long (>=MINRUN, so never the checkerboard), stop
    at the first short or distant one. nkanji is used only to sanity-check the
    answer against the 18px glyph pitch.
    """
    ink = [x for x in range(256) if any(g[y][x] for y in range(len(g)))]
    assert ink, "no ink on this row"
    runs, st = [], None
    for x in range(257):
        on = x < 256 and x in ink
        if on and st is None:
            st = x
        elif not on and st is not None:
            runs.append((st, x - 1))
            st = None
    left, right = runs[-1]
    for a, b in reversed(runs[:-1]):
        if left - b - 1 <= 2 and (b - a + 1) >= MINRUN:
            left = a
        else:
            break
    expect = RIGHT - PITCH * nkanji + 1
    assert abs(left - expect) <= 5, (
        "label box x%d-%d does not match %d glyphs at %dpx pitch (expected "
        "left %d)" % (left, right, nkanji, PITCH, expect))
    return left, right


def render(text, w, h):
    big = 4
    img = Image.new("L", (w * big, h * big), 0)
    d = ImageDraw.Draw(img)
    # Cap the starting size instead of filling the box. The japanese labels are
    # all one 18px glyph height, so letting "OK" grow to fill 38px while
    # "ALIAS" shrinks to fit the same width makes the column look ransom-note.
    size = min(MAXPT, h - 4) * big
    font = ImageFont.truetype(FONT, size)
    bb = d.textbbox((0, 0), text, font=font)
    while (bb[2] - bb[0]) > (w - 3) * big and size > 6 * big:
        size -= big
        font = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((w * big - tw) // 2 - bb[0], (h * big - th) // 2 - bb[1]),
           text, fill=255, font=font)
    a = img.resize((w, h), Image.LANCZOS).load()
    out = [CLEAR] * (w * h)
    for y in range(h):
        for x in range(w):
            if a[x, y] >= 128 and x + 2 < w and y + 2 < h:
                out[(y + 2) * w + (x + 2)] = SHADOW
    for y in range(h):
        for x in range(w):
            v = a[x, y]
            if v >= 160:
                out[y * w + x] = FILL
            elif v >= 56:
                out[y * w + x] = EDGE
    return out


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    preview_only = "--preview-only" in sys.argv
    start = KVMDATA_LBA * SECTOR + TEX_OFF_IN_FILE
    nrows = BLOCK_Y1 - BLOCK_Y0 + 1
    mode = "rb" if preview_only else "r+b"
    with open(iso_path, mode) as iso:
        iso.seek(start)
        hdr = iso.read(52)
        assert hdr[:4] == b"TIM2", "no TIM2 here - layout moved?"
        tot, clutsz, imgsz, hdrsz, clutcol = struct.unpack_from("<IIIHH", hdr, 16)
        w, h = struct.unpack_from("<HH", hdr, 36)
        assert (w, h, imgsz) == (256, 256, 32768), "unexpected texture shape"
        pix = start + 16 + hdrsz

        iso.seek(pix + BLOCK_Y0 * ROWBYTES)
        block = bytearray(iso.read(nrows * ROWBYTES))
        orig = open(BACKUP, "rb").read() if os.path.exists(BACKUP) else None

        if revert:
            assert orig, "no saved original to revert to"
            iso.seek(pix + BLOCK_Y0 * ROWBYTES)
            iso.write(orig)
            print("reverted the profile labels to japanese")
            return
        if orig is None and not preview_only:
            open(BACKUP, "wb").write(bytes(block))
            print("saved the japanese block (%d bytes)" % len(block))
        src = bytearray(orig) if orig else bytearray(block)

        for y0, y1, jp, en, nk in BANDS:
            g = unpack(src, y0)
            left, right = measure(g, nk)
            bw = right - left + 1
            bh = y1 - y0 + 1
            m = render(en, bw, bh)
            for yy in range(bh):
                row = (y0 - BLOCK_Y0 + yy) * ROWBYTES
                for xx in range(bw):
                    x = left + xx
                    b = block[row + x // 2]
                    v = m[yy * bw + xx]
                    block[row + x // 2] = ((b & 0xF0) | v) if x % 2 == 0 \
                        else ((b & 0x0F) | (v << 4))
            print("  %-8s -> %-7s box x %3d-%3d (w=%2d) rows %d-%d"
                  % (jp, en, left, right, bw, y0, y1))

        if not preview_only:
            iso.seek(pix + BLOCK_Y0 * ROWBYTES)
            iso.write(bytes(block))
            print("painted (sha1 %s)" % hashlib.sha1(bytes(block)).hexdigest()[:12])

        img = Image.new("L", (256, nrows))
        p = img.load()
        for y in range(nrows):
            for x in range(0, 256, 2):
                b = block[y * ROWBYTES + x // 2]
                p[x, y] = (b & 15) * 17
                p[x + 1, y] = (b >> 4) * 17
        img.crop((150, 0, 256, nrows)).resize((106 * 5, nrows * 5),
                                              Image.NEAREST).save(PREVIEW)
        print("preview: %s" % os.path.relpath(PREVIEW, ROOT))


if __name__ == "__main__":
    main()
