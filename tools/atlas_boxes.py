# -*- coding: utf-8 -*-
"""Find individual label rectangles in a 4bpp TIM2 atlas and emit a numbered
montage so each box can be identified by eye.

Usage: atlas_boxes.py <container> <tim2_offset_hex> <outdir>
"""
import os, struct, sys, json
from PIL import Image, ImageDraw

def load4(d, o):
    tot, cs, isz, hs, cc, pf, mm, ct, it, w, h = struct.unpack_from("<IIIHHBBBBHH", d, o + 16)
    pix = o + 16 + hs
    idx = [[0]*w for _ in range(h)]
    for y in range(h):
        base = pix + y*(w//2)
        for x in range(0, w, 2):
            b = d[base + x//2]
            idx[y][x] = b & 0xF
            idx[y][x+1] = b >> 4
    return idx, w, h, pix, isz, pix+isz, cs, cc

def main():
    src, off, outdir = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    d = open(src, "rb").read()
    idx, w, h, pix, isz, clut, cs, cc = load4(d, off)
    # horizontal bands
    rowocc = [sum(1 for x in range(w) if idx[y][x]) for y in range(h)]
    bands = []; y = 0
    while y < h:
        if rowocc[y]:
            s = y
            while y < h and rowocc[y]: y += 1
            bands.append((s, y-1))
        else: y += 1
    boxes = []
    for (y0, y1) in bands:
        colocc = [sum(1 for yy in range(y0, y1+1) if idx[yy][x]) for x in range(w)]
        x = 0
        while x < w:
            if colocc[x]:
                s = x; gap = 0
                while x < w:
                    if colocc[x]: gap = 0
                    else:
                        gap += 1
                        if gap >= 5: break
                    x += 1
                e = x - gap
                # tighten vertically for this column range
                yy0 = next((yy for yy in range(y0, y1+1) if any(idx[yy][xx] for xx in range(s, e+1))), y0)
                yy1 = next((yy for yy in range(y1, y0-1, -1) if any(idx[yy][xx] for xx in range(s, e+1))), y1)
                if e - s >= 3 and yy1 - yy0 >= 3:
                    boxes.append([s, yy0, e, yy1])
            else: x += 1
    print("boxes: %d" % len(boxes))
    json.dump(boxes, open(os.path.join(outdir, "boxes.json"), "w"))
    # montage: each box cropped, scaled, numbered
    SC = 2
    cells = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        bw, bh = x1-x0+1, y1-y0+1
        im = Image.new("RGB", (bw, bh), (20, 20, 20))
        p = im.load()
        for yy in range(bh):
            for xx in range(bw):
                v = idx[y0+yy][x0+xx]
                p[xx, yy] = (0, 0, 0) if v == 0 else (255, 255, 255) if v in (1, 15) else (255, 170, 60)
        im = im.resize((bw*SC, bh*SC), Image.NEAREST)
        cells.append((i, im, (x0, y0, x1, y1)))
    CW = max(c[1].width for c in cells) + 90
    CH = max(c[1].height for c in cells) + 10
    cols = 3
    rows = (len(cells)+cols-1)//cols
    sheet = Image.new("RGB", (cols*CW, rows*CH), (35, 35, 35))
    dr = ImageDraw.Draw(sheet)
    for i, im, r in cells:
        cx = (i % cols)*CW; cy = (i//cols)*CH
        dr.text((cx+3, cy+3), "%d" % i, fill=(120, 255, 120))
        dr.text((cx+3, cy+16), "%d,%d" % (r[0], r[1]), fill=(150, 150, 150))
        sheet.paste(im, (cx+60, cy+3))
    sheet.save(os.path.join(outdir, "boxes.png"))
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        print("  %2d  x%3d..%3d y%3d..%3d  (%dx%d)" % (i, x0, x1, y0, y1, x1-x0+1, y1-y0+1))

if __name__ == "__main__":
    main()
