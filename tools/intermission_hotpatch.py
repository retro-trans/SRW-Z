# -*- coding: utf-8 -*-
"""Live-iterate the intermission label fonts via PINE.

Renders label cells with the v2 style (full cell height, horizontal
squeeze instead of point-size shrink, stroked outline like the BS. glyph)
and writes them either into EE RAM (hot test against the user's save
state) or into the ISO (ship). RAM page pixel bases found by needle-match
against the 18:56 save state:
  p05 0xC5A9E0   p10 0xDC2800 and 0xDCAAF0 (two live copies)   p06 0xC62C30

Usage:
  intermission_hotpatch.py ram    write cells into the running game
  intermission_hotpatch.py iso <path>  write cells into the ISO
"""
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

FILL, EDGE, SHADOW, CLEAR = 15, 11, 4, 0
FONT = r"C:\Windows\Fonts\georgiab.ttf"
KVMDATA_LBA, SECTOR, ROWBYTES = 1289810, 2048, 128

RAM_PIX = {0x28B40: [0xC5A9E0], 0x52070: [0xDC2800, 0xDCAAF0]}

# (page texoff, x0, y0, x1, y1, text, style)
CELLS = [
    (0x28B40, 142,  2, 166, 30, "EP", {"baseline": 22}),
    (0x28B40, 208,  0, 255, 32, "Funds", {"floor": 0.62, "baseline": 24}),
    (0x28B40, 148, 40, 235, 63, "SR Points", {"baseline": 19}),
]
# p10 ticker cells (REVERTED to JP - marquee stays Japanese per user; kept
# here for future custom-font experiments):
#   (0x52070,   2,  4,  18, 20, "EP", {"baseline": 14}),
#   (0x52070,  22,  4,  38, 20, "", {}),
#   (0x52070,  60,  4, 150, 20, "cleared!", {"baseline": 14}),
#   (0x52070,  70, 28, 103, 44, "SORTIE", {"pt": 52, "baseline": 14, "group": "sq"}),
#   (0x52070, 106, 28, 140, 44, "SQUAD", {"pt": 52, "baseline": 14, "group": "sq"}),


def auto_pt(text, w, h, floor):
    big = 4
    pt = (h - 2) * big
    while pt > 6 * big:
        font = ImageFont.truetype(FONT, pt)
        img = Image.new("L", (8, 8), 0)
        dr = ImageDraw.Draw(img)
        bb = dr.textbbox((0, 0), text, font=font)
        if (w - 2) * big >= (bb[2] - bb[0]) * floor:
            break
        pt -= big
    return pt


def render_cell(text, w, h, style=None):
    """v3: baseline-anchored (JP glyphs sit on the cell floor), squeeze-fit,
    stroked outline. style: floor, baseline (row of text baseline within
    cell), pt (explicit size override)."""
    st = style or {}
    out = [CLEAR] * (w * h)
    if not text:
        return out
    big = 4
    floor_ = st.get("floor", 0.74)
    pt = st.get("pt") or auto_pt(text, w, h, floor_)
    font = ImageFont.truetype(FONT, pt)
    ascent, descent = font.getmetrics()
    img = Image.new("L", (w * big * 6, h * big * 3), 0)
    dr = ImageDraw.Draw(img)
    bb = dr.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    dr.text((-bb[0], -bb[1]), text, fill=255, font=font)
    natural = img.crop((0, 0, tw, max(th, 1)))
    sx = min(1.0, (w - 2) * big / float(tw))
    tgt_w = max(1, int(tw * sx))
    natural = natural.resize((tgt_w, th), Image.LANCZOS)
    # baseline row within the cropped glyph image
    bl_in_crop = ascent - bb[1]
    bl_row = st.get("baseline", h - 3)
    paste_y = bl_row * big - bl_in_crop
    canvas = Image.new("L", (w * big, h * big), 0)
    canvas.paste(natural, (((w - 2) * big - tgt_w) // 2, paste_y))
    small = canvas.resize((w, h), Image.LANCZOS)
    a = small.load()
    sh = 1 if h <= 20 else 2
    # v4 layer structure, sampled from the JP glyphs:
    #   15 fill core -> 11 light inner AA -> 8 dark outline ring -> 4 shadow
    AA_IN, RING = 11, 8
    fillmask = [[a[x, y] >= 128 for x in range(w)] for y in range(h)]

    def near(mask, xx, yy):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x2, y2 = xx + dx, yy + dy
                if 0 <= x2 < w and 0 <= y2 < h and mask[y2][x2]:
                    return True
        return False
    for yy in range(h):
        for xx in range(w):
            if fillmask[yy][xx]:
                out[yy * w + xx] = FILL
    # light AA: strong-ish alpha hugging the fill
    aa = [[False] * w for _ in range(h)]
    for yy in range(h):
        for xx in range(w):
            if not fillmask[yy][xx] and a[xx, yy] >= 60 \
                    and near(fillmask, xx, yy):
                out[yy * w + xx] = AA_IN
                aa[yy][xx] = True
    # dark ring around fill+AA
    solid = [[fillmask[y][x] or aa[y][x] for x in range(w)] for y in range(h)]
    for yy in range(h):
        for xx in range(w):
            if out[yy * w + xx] == CLEAR and near(solid, xx, yy):
                out[yy * w + xx] = RING
    # shadow last, only into clear space
    for yy in range(h - 1, -1, -1):
        for xx in range(w - 1, -1, -1):
            if fillmask[yy][xx] and xx + sh < w and yy + sh < h \
                    and out[(yy + sh) * w + (xx + sh)] == CLEAR:
                out[(yy + sh) * w + (xx + sh)] = SHADOW
    return out


def cell_words(texoff, x0, y0, x1, y1, idx):
    """-> list of (ram-relative byte offset, packed row bytes) per row."""
    w = x1 - x0
    rows = []
    for yy, y in enumerate(range(y0, y1)):
        row = bytearray()
        for xb in range(0, w, 2):
            lo = idx[yy * w + xb]
            hi = idx[yy * w + xb + 1] if xb + 1 < w else CLEAR
            row.append(lo | (hi << 4))
        rows.append((y * ROWBYTES + x0 // 2, bytes(row)))
    return rows


def main():
    mode = sys.argv[1]
    # grouped cells share the smallest auto pt so they match visually
    group_pt = {}
    for texoff, x0, y0, x1, y1, text, style in CELLS:
        g = (style or {}).get("group")
        if g and text:
            p = auto_pt(text, x1 - (x0 & ~1), y1 - y0, (style or {}).get("floor", 0.74))
            group_pt[g] = min(group_pt.get(g, 9999), p)
    cells = []
    for texoff, x0, y0, x1, y1, text, style in CELLS:
        if x0 % 2:
            x0 -= 1
        st = dict(style or {})
        if st.get("group") in group_pt:
            st["pt"] = group_pt[st["group"]]
        idx = render_cell(text, x1 - x0, y1 - y0, st)
        cells.append((texoff, x0, y0, x1, y1, cell_words(texoff, x0, y0, x1, y1, idx)))
    if mode == "ram":
        from pine_read import Pine
        p = Pine()
        n = 0
        for texoff, x0, y0, x1, y1, rows in cells:
            for base in RAM_PIX.get(texoff, []):
                for off, data in rows:
                    addr = base + off
                    # align to 4: pad with live bytes at the edges
                    a0 = addr & ~3
                    a1 = (addr + len(data) + 3) & ~3
                    live = bytearray()
                    words = p.read32_batch(list(range(a0, a1, 4)))
                    for wv in words:
                        live += wv.to_bytes(4, "little")
                    live[addr - a0:addr - a0 + len(data)] = data
                    for i in range(0, len(live), 4):
                        p.write32(a0 + i, int.from_bytes(live[i:i+4], "little"))
                        n += 1
        print("wrote %d words to RAM" % n)
    elif mode == "iso":
        iso = open(sys.argv[2], "r+b")
        for texoff, x0, y0, x1, y1, rows in cells:
            pixbase = KVMDATA_LBA * SECTOR + texoff + 16 + 48
            for off, data in rows:
                iso.seek(pixbase + off)
                iso.write(data)
        iso.close()
        print("ISO painted (v2 fonts)")
    else:
        raise SystemExit("mode must be ram or iso")


if __name__ == "__main__":
    main()
