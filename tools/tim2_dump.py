# -*- coding: utf-8 -*-
"""Decode TIM2 images out of a container (e.g. DATA_JTIM.BIN) to PNG.

TIM2: 'TIM2' hdr(16) then per image: imgHdr(hs) + pixels(isz) + clut(cs).
PS2 palettised CLUTs are stored with bits 3/4 of the index swapped (8bpp),
and alpha is 0..128 -> scale to 0..255.

Usage: tim2_dump.py <container> <outdir> [index ...]
"""
import os, re, struct, sys
from PIL import Image

def unswizzle_clut8(pal):
    out = list(pal)
    for i in range(len(pal)):
        j = (i & 0xE7) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)
        out[i] = pal[j]
    return out

def read_clut(d, off, colors, bpp_bytes=4):
    pal = []
    for i in range(colors):
        r, g, b, a = d[off + i*4: off + i*4 + 4]
        a = min(255, a * 2)
        pal.append((r, g, b, a))
    return pal

def main():
    src, outdir = sys.argv[1], sys.argv[2]
    want = set(int(x) for x in sys.argv[3:]) if len(sys.argv) > 3 else None
    os.makedirs(outdir, exist_ok=True)
    d = open(src, "rb").read()
    offs = [m.start() for m in re.finditer(b'TIM2', d)]
    for idx, o in enumerate(offs):
        if want is not None and idx not in want:
            continue
        ho = o + 16
        tot, cs, isz, hs, cc, pf, mm, ct, it, w, h = struct.unpack_from("<IIIHHBBBBHH", d, ho)
        pix = ho + hs
        clut = pix + isz
        if it == 5:      # 8bpp
            pal = read_clut(d, clut, cc)
            if cc == 256:
                pal = unswizzle_clut8(pal)
            img = Image.new("RGBA", (w, h))
            px = img.load()
            for y in range(h):
                row = d[pix + y*w: pix + (y+1)*w]
                for x in range(w):
                    px[x, y] = pal[row[x]]
        elif it == 4:    # 4bpp
            pal = read_clut(d, clut, cc)
            img = Image.new("RGBA", (w, h))
            px = img.load()
            for y in range(h):
                base = pix + y*(w//2)
                for x in range(0, w, 2):
                    b = d[base + x//2]
                    px[x, y] = pal[b & 0xF]
                    px[x+1, y] = pal[b >> 4]
        elif it == 3:    # 32bpp
            img = Image.frombytes("RGBA", (w, h), d[pix:pix+w*h*4])
            r, g, b, a = img.split()
            a = a.point(lambda v: min(255, v*2))
            img = Image.merge("RGBA", (r, g, b, a))
        elif it == 2:    # 24bpp
            img = Image.frombytes("RGB", (w, h), d[pix:pix+w*h*3]).convert("RGBA")
        elif it == 1:    # 16bpp RGBA5551
            img = Image.new("RGBA", (w, h))
            px = img.load()
            for y in range(h):
                base = pix + y*w*2
                for x in range(w):
                    v = d[base + x*2] | (d[base + x*2 + 1] << 8)
                    px[x, y] = (((v) & 31) << 3, ((v >> 5) & 31) << 3,
                                ((v >> 10) & 31) << 3, 255 if (v >> 15) else 0)
        else:
            print("img %d: unsupported type %d" % (idx, it)); continue
        # composite on mid-grey so transparent art stays visible
        bg = Image.new("RGBA", img.size, (110, 110, 110, 255))
        flat = Image.alpha_composite(bg, img)
        p = os.path.join(outdir, "tim%02d_%dx%d.png" % (idx, w, h))
        flat.convert("RGB").save(p)
        print("img %d -> %s (%dx%d type%d)" % (idx, p, w, h, it))

if __name__ == "__main__":
    main()
