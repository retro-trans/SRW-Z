# -*- coding: utf-8 -*-
"""Compose the intermission bar labels from HARVESTED original glyphs.

User request: gold bar text must look exactly like the hand-drawn "BS."
art. There is no font file behind it - the letters are sheet art - but
KVMDATA page 4 carries the same serif family in enough words to spell the
labels in caps. Letters are cut from p04 (index bitmaps, shadows and
outline included) and pasted into the p05 label cells; p04/p05 CLUTs
differ only in tint slots, and the reinterpretation under p05's palette
matches the BS. gold accents.

Donor rows on p04 (y ranges include shadow rows):
  row2  y49..65  "SIZE" "LMS" "UP" "MOON" ... "TR I"   (~13px, primary)
  row3  y67..79  "HARD NORMAL EASY"                    (D donor)
  row4  y83..95  "FORMATION"                           (F donor)

Usage:
  harvest_labels.py ram          hot-write into the running game via PINE
  harvest_labels.py iso <path>   write into the ISO
  harvest_labels.py preview      dump analysis/harvest_preview.png only
"""
import struct
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

KVM_LBA, SECTOR, ROWBYTES = 1289810, 2048, 128
P04, P05 = 0x20900, 0x28B40
RAM_P05 = 0xC5A9E0

ISO = r"E:\Projects\SRW Z\_work\iso\srwz_restore.bin"


def load_page(texoff):
    f = open(ISO, "rb")
    f.seek(KVM_LBA * SECTOR + texoff + 16 + 48)
    return f.read(32768)


def getpx(d, x, y):
    b = d[y * ROWBYTES + x // 2]
    return (b >> 4) if (x & 1) else (b & 15)


def split_word(d, x0, x1, y0, y1, n):
    """Cut a word image into n glyphs at the n-1 thinnest ink columns."""
    dens = [sum(1 for y in range(y0, y1) if getpx(d, x, y)) for x in range(x0, x1)]
    w = x1 - x0
    approx = [round(w * k / float(n)) for k in range(1, n)]
    cuts = []
    for ap in approx:
        lo, hi = max(1, ap - 3), min(w - 1, ap + 4)
        best = min(range(lo, hi), key=lambda i: (dens[i], abs(i - ap)))
        cuts.append(best)
    edges = [0] + cuts + [w]
    return [(x0 + edges[k], x0 + edges[k + 1]) for k in range(n)]


def glyph(d, x0, x1, y0, y1):
    """Trim empty columns; return (w, h, index rows)."""
    while x0 < x1 and all(getpx(d, x0, y) == 0 for y in range(y0, y1)):
        x0 += 1
    while x1 > x0 and all(getpx(d, x1 - 1, y) == 0 for y in range(y0, y1)):
        x1 -= 1
    rows = [[getpx(d, x, y) for x in range(x0, x1)] for y in range(y0, y1)]
    return rows


def build_atlas():
    p4 = load_page(P04)
    atlas = {}
    # primary row (SIZE / LMS / UP / MOON / TR I), y49..65
    for word, x0, x1 in (("SIZE", 2, 37), ("LMS", 40, 80), ("UP", 82, 107),
                         ("MOON", 108, 149), ("TRI", 210, 250)):
        for ch, (gx0, gx1) in zip(word, split_word(p4, x0, x1, 50, 65, len(word))):
            atlas.setdefault(ch, glyph(p4, gx0, gx1, 50, 65))
    # D from HARD, F from FORMATION - explicit boxes (ruler-measured)
    atlas["D"] = glyph(p4, 31, 42, 67, 80)
    atlas["F"] = glyph(p4, 4, 14, 83, 96)
    return atlas


# (cell x0,y0,x1,y1 on p05, text, bottom row for glyph baseline)
LABELS = [
    # (cell, text, glyph bottom row, letter spacing)
    # The painted labels sat lower than the game's own serif numerals beside
    # them (measured off a capture: FUNDS' baseline was 4 px below "118,820").
    # Raised per the user's eye: FUNDS by 3 px, EP by 4 px.
    # 5th field = shrink: render the glyphs N px shorter (width follows).
    ((142,  2, 166, 30), "EP", 16, 1, 0),   # 8 px up; 16 is the cell ceiling
    ((208,  0, 255, 32), "FUNDS", 19, -2, 0),
    ((148, 40, 235, 63), "SR POINTS", 62, 1, 2),
]


def shrink_glyph(g, px):
    """Return the glyph `px` pixels shorter, width scaled to match.

    Nearest-neighbour on the CLUT INDEX grid - the indices are fill/edge/
    shadow, not colours, so they must not be blended.
    """
    if px <= 0:
        return g
    from PIL import Image
    gh, gw = len(g), len(g[0])
    nh = max(1, gh - px)
    nw = max(1, int(round(gw * nh / float(gh))))
    im = Image.new("L", (gw, gh))
    im.putdata([v for row in g for v in row])
    im = im.resize((nw, nh), Image.NEAREST)
    d = list(im.getdata())
    return [d[y * nw:(y + 1) * nw] for y in range(nh)]


def compose(atlas, cellw, cellh, text, bottom_in_cell, y0, spacing=1, shrink=0):
    if shrink:
        atlas = {k: shrink_glyph(v, shrink) for k, v in atlas.items()}
    out = [[0] * cellw for _ in range(cellh)]
    widths = [(len(atlas[c][0]) if c != " " else 4) for c in text]
    total = sum(widths) + (len(text) - 1) * spacing
    x = max(0, (cellw - total) // 2)
    for c in text:
        if c == " ":
            x += 5
            continue
        g = atlas[c]
        gh, gw = len(g), len(g[0])
        ytop = (bottom_in_cell - y0) - gh + 1
        for gy in range(gh):
            for gx in range(gw):
                v = g[gy][gx]
                if v and 0 <= ytop + gy < cellh and 0 <= x + gx < cellw                         and not (out[ytop + gy][x + gx] and v == 4):
                    out[ytop + gy][x + gx] = v
        x += gw + spacing
    return out


def main():
    mode = sys.argv[1]
    atlas = build_atlas()
    print("atlas letters:", "".join(sorted(atlas)))
    cells = []
    for (x0, y0, x1, y1), text, bottom, spacing, shrink in LABELS:
        if x0 % 2:
            x0 -= 1
        grid = compose(atlas, x1 - x0, y1 - y0, text, bottom, y0, spacing, shrink)
        rows = []
        for yy, rowvals in enumerate(grid):
            row = bytearray()
            for xb in range(0, len(rowvals), 2):
                lo = rowvals[xb]
                hi = rowvals[xb + 1] if xb + 1 < len(rowvals) else 0
                row.append(lo | (hi << 4))
            rows.append(((y0 + yy) * ROWBYTES + x0 // 2, bytes(row)))
        cells.append(rows)
    if mode == "preview":
        from PIL import Image
        f = open(ISO, "rb")
        f.seek(KVM_LBA * SECTOR + P05 + 16)
        tot, clutsz, img, hdr = struct.unpack("<IIIH", f.read(14))
        f.seek(KVM_LBA * SECTOR + P05 + 16 + hdr + img)
        cl = f.read(clutsz)
        sheets = []
        for ((x0, y0, x1, y1), text, bottom, spacing, shrink), rows in zip(LABELS, cells):
            w = (x1 - (x0 & ~1))
            h = y1 - y0
            im = Image.new("RGBA", (w, h), (10, 10, 60, 255))
            px = im.load()
            grid = compose(atlas, w, h, text, bottom, y0, spacing, shrink)
            for yy in range(h):
                for xx in range(w):
                    v = grid[yy][xx]
                    if v:
                        r, g, b, a = cl[v * 4:v * 4 + 4]
                        px[xx, yy] = (r, g, b, 255)
            sheets.append(im)
        W = max(i.width for i in sheets) + 8
        H = sum(i.height + 4 for i in sheets)
        out = Image.new("RGBA", (W, H), (10, 10, 60, 255))
        y = 2
        for im in sheets:
            out.paste(im, (4, y))
            y += im.height + 4
        out.resize((W * 5, H * 5), Image.NEAREST).save(
            r"E:\Projects\SRW Z\_work\analysis\harvest_preview.png")
        print("preview saved")
        return
    if mode == "ram":
        from pine_read import Pine
        p = Pine()
        n = 0
        for rows in cells:
            for off, data in rows:
                addr = RAM_P05 - (16 + 48) + (16 + 48) + off - 0  # pix base + off
                addr = RAM_P05 + off
                a0 = addr & ~3
                a1 = (addr + len(data) + 3) & ~3
                live = bytearray()
                for wv in p.read32_batch(list(range(a0, a1, 4))):
                    live += wv.to_bytes(4, "little")
                live[addr - a0:addr - a0 + len(data)] = data
                for i in range(0, len(live), 4):
                    p.write32(a0 + i, int.from_bytes(live[i:i + 4], "little"))
                    n += 1
        print("wrote %d words" % n)
    elif mode == "iso":
        iso = open(sys.argv[2], "r+b")
        pixbase = KVM_LBA * SECTOR + P05 + 16 + 48
        for rows in cells:
            for off, data in rows:
                iso.seek(pixbase + off)
                iso.write(data)
        iso.close()
        print("ISO painted (harvested glyphs)")


if __name__ == "__main__":
    main()
