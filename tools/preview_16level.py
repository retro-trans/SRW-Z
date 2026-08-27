# -*- coding: utf-8 -*-
"""Show 4-level vs 16-level alpha for the SAME face, at real size.

The engine's master font is 4bpp - 16 alpha levels - and the game's own japanese
glyphs use all 16. Our Latin atlas stores 2bpp (4 levels) purely to fit the
cave, and that is what makes the edges look stepped. This renders MS Gothic
both ways so the gain can be judged before rewriting the stamper.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

CW, ROWS, NART = 12, 24, 69
BASELINE, SS = 19, 8
CHARS = [0x2E,0x22,0x27,0x21,0x2C,0x2D,0x3F]+list(range(0x30,0x3A))+ \
        list(range(0x41,0x5B))+list(range(0x61,0x7B))
IDX = {chr(c): i for i, c in enumerate(CHARS)}
LINES = ["Lord Shiruha, Lord Goushi,",
         "Now, by the Sun's fierce festival",
         "Illiterate militia in Wisconsin"]

def render(path, cap, levels):
    for pt in range(8, 80):
        f = ImageFont.truetype(path, pt)
        im = Image.new("L", (pt*4, pt*4), 0)
        ImageDraw.Draw(im).text((5,5), "H", font=f, fill=255)
        bb = im.getbbox()
        if bb and (bb[3]-bb[1]) >= cap: break
    big = ImageFont.truetype(path, pt*SS)
    out = []
    for code in CHARS:
        im = Image.new("L", (CW*SS*2, ROWS*SS*2), 0)
        ImageDraw.Draw(im).text((1*SS, BASELINE*SS), chr(code), font=big, fill=255, anchor="ls")
        im = im.crop((0,0,CW*SS,ROWS*SS)).resize((CW,ROWS), Image.LANCZOS)
        p = im.load()
        n = levels - 1
        out.append([[int(round(p[x,y]/255.0*n)) for x in range(CW)] for y in range(ROWS)])
    return out, levels

def draw(img, d, gl, levels, text, x0, y0, s, tint):
    x = x0
    for ch in text:
        if ch == " ": x += 6*s; continue
        g = IDX.get(ch)
        if g is None: x += 12*s; continue
        px = gl[g]
        cols = [c for c in range(CW) if any(px[r][c] for r in range(ROWS))]
        adv = (cols[-1]+2) if cols else CW
        for r in range(ROWS):
            for c in range(CW):
                v = px[r][c]
                if v:
                    a = v/float(levels-1)
                    col = tuple(int(a*t) for t in tint)
                    d.rectangle([x+c*s, y0+r*s, x+(c+1)*s-1, y0+(r+1)*s-1], fill=col)
        x += adv*s
    return x-x0

def main():
    path = "C:/Windows/Fonts/msgothic.ttc"
    out = sys.argv[1] if len(sys.argv) > 1 else "analysis/preview_16.png"
    g4, _ = render(path, 18, 4)
    g8, _ = render(path, 18, 8)
    g16, _ = render(path, 18, 16)
    sets = [("4 LEVELS - what ships today", g4, 4, (245,245,245)),
            ("8 LEVELS - 3bpp, fits in place", g8, 8, (150,235,150)),
            ("16 LEVELS - 4bpp, needs 916 B more", g16, 16, (150,200,255))]
    W, H = 1050, 40 + len(LINES)*3*(ROWS*3+14) + len(LINES)*12 + 130
    img = Image.new("RGB", (W,H), (16,18,24)); d = ImageDraw.Draw(img)
    d.text((14,10), "same face, same size - only the number of alpha levels differs", fill=(190,200,215))
    y = 32
    for t in LINES:
        for nm, gl, lv, tint in sets:
            d.text((14,y-11), nm, fill=tint)
            draw(img, d, gl, lv, t, 14, y, 3, tint); y += ROWS*3+14
        y += 12
    d.text((14,y), "actual size:", fill=(190,200,215)); y += 14
    for nm, gl, lv, tint in sets:
        draw(img, d, gl, lv, LINES[1], 14, y, 1, tint); y += ROWS+4
    img.save(out); print("wrote", out)

main()
