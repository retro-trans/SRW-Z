# -*- coding: utf-8 -*-
"""Decode every TIM2 in the given containers and tile them into contact sheets
for quick visual scanning. Usage: tim2_sheet.py <outdir> <file> [file ...]"""
import os, re, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tim2_dump as T

CELL = 208

def decode(d, o):
    ho = o + 16
    tot, cs, isz, hs, cc, pf, mm, ct, it, w, h = struct.unpack_from("<IIIHHBBBBHH", d, ho)
    if not (0 < w <= 2048 and 0 < h <= 2048):
        return None
    pix = ho + hs; clut = pix + isz
    if pix + isz > len(d):
        return None
    try:
        if it == 5:
            pal = T.read_clut(d, clut, cc)
            if cc == 256: pal = T.unswizzle_clut8(pal)
            img = Image.new("RGBA", (w, h)); px = img.load()
            for y in range(h):
                row = d[pix+y*w: pix+(y+1)*w]
                if len(row) < w: return None
                for x in range(w): px[x, y] = pal[row[x]]
        elif it == 4:
            pal = T.read_clut(d, clut, cc)
            img = Image.new("RGBA", (w, h)); px = img.load()
            for y in range(h):
                base = pix + y*(w//2)
                for x in range(0, w, 2):
                    b = d[base + x//2]
                    px[x, y] = pal[b & 0xF]; px[x+1, y] = pal[b >> 4]
        elif it == 3:
            img = Image.frombytes("RGBA", (w, h), d[pix:pix+w*h*4])
        elif it == 2:
            img = Image.frombytes("RGB", (w, h), d[pix:pix+w*h*3]).convert("RGBA")
        elif it == 1:
            img = Image.new("RGBA", (w, h)); px = img.load()
            for y in range(h):
                base = pix + y*w*2
                for x in range(w):
                    v = d[base+x*2] | (d[base+x*2+1] << 8)
                    px[x, y] = (((v)&31)<<3, ((v>>5)&31)<<3, ((v>>10)&31)<<3, 255 if (v>>15) else 0)
        else:
            return None
    except Exception:
        return None
    bg = Image.new("RGBA", img.size, (105, 105, 105, 255))
    return Image.alpha_composite(bg, img).convert("RGB")

def main():
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    tiles = []
    for f in sys.argv[2:]:
        d = open(f, "rb").read()
        base = os.path.basename(f)
        for idx, m in enumerate(re.finditer(b'TIM2', d)):
            img = decode(d, m.start())
            if img is None: continue
            img.thumbnail((CELL, CELL))
            tiles.append((base, idx, img))
    print("decoded %d tiles" % len(tiles))
    per = 5
    pages = [tiles[i:i+per*4] for i in range(0, len(tiles), per*4)]
    for pi, page in enumerate(pages):
        rows = (len(page)+per-1)//per
        sheet = Image.new("RGB", (per*CELL, rows*CELL), (30, 30, 30))
        for i, (base, idx, img) in enumerate(page):
            x = (i % per)*CELL; y = (i//per)*CELL
            sheet.paste(img, (x + (CELL-img.width)//2, y + (CELL-img.height)//2))
        p = os.path.join(outdir, "sheet%02d.png" % pi)
        sheet.save(p)
        print("%s : %s" % (p, ", ".join("%s#%d" % (b, i) for b, i, _ in page)))

if __name__ == "__main__":
    main()
