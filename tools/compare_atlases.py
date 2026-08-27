# -*- coding: utf-8 -*-
"""Render the same sample text with the shipped atlas and candidate atlases."""
import sys
from PIL import Image, ImageDraw
CW, ROWS, GB, NART = 12, 24, 72, 69
LEVELS = [0, 90, 175, 255]
CHARS = [0x2E,0x22,0x27,0x21,0x2C,0x2D,0x3F]+list(range(0x30,0x3A))+ \
        list(range(0x41,0x5B))+list(range(0x61,0x7B))
IDX = {chr(c): i for i, c in enumerate(CHARS)}
LINES = ["Illiterate militia in Wisconsin",
         "Now, by the Sun's fierce festival",
         "Wow! Mmm... Why? Warm summer"]

def unpack(b):
    out=[]
    for g in range(NART):
        cell=b[g*GB:(g+1)*GB]; px=[]
        for r in range(ROWS):
            t=cell[r*3:r*3+3]
            bits=(t[0]<<16)|(t[1]<<8)|t[2]
            px.append([(bits>>(22-2*x))&3 for x in range(CW)])
        out.append(px)
    return out

def shipped(iso):
    f=open(iso,"rb"); f.seek(455*2048); elf=f.read(3471624); f.close()
    base=0x34D770+(0x78A5B0-0x78A070)
    return unpack(elf[base:base+NART*GB])

def draw(img,d,gl,text,x0,y0,s,col):
    x=x0
    for ch in text:
        if ch==" ": x+=6*s; continue
        g=IDX.get(ch)
        if g is None: x+=12*s; continue
        px=gl[g]
        cols=[c for c in range(CW) if any(px[r][c] for r in range(ROWS))]
        adv=(cols[-1]+2) if cols else CW
        for r in range(ROWS):
            for c in range(CW):
                v=px[r][c]
                if v:
                    lv=LEVELS[v]
                    d.rectangle([x+c*s,y0+r*s,x+(c+1)*s-1,y0+(r+1)*s-1],
                                fill=(int(lv*col[0]/255),int(lv*col[1]/255),int(lv*col[2]/255)))
        x+=adv*s
    return x-x0

def main():
    iso=sys.argv[1]; out=sys.argv[2]
    sets=[("SHIPPED  MS Gothic",shipped(iso),(245,245,245))]
    for spec in sys.argv[3:]:
        name,path=spec.split("=",1)
        sets.append((name,unpack(open(path,"rb").read()),(150,235,150) if len(sets)==1 else (150,200,255)))
    W,H=1050,40+len(LINES)*len(sets)*(ROWS*3+14)+len(LINES)*12+90
    img=Image.new("RGB",(W,H),(16,18,24)); d=ImageDraw.Draw(img)
    d.text((14,10),"same text, each atlas, 3x then 1:1",fill=(190,200,215))
    y=32
    for t in LINES:
        for nm,gl,col in sets:
            d.text((14,y-11),nm,fill=col)
            draw(img,d,gl,t,14,y,3,col); y+=ROWS*3+14
        y+=12
    d.text((14,y),"actual size:",fill=(190,200,215)); y+=14
    for nm,gl,col in sets:
        draw(img,d,gl,LINES[2],14,y,1,col); y+=ROWS+4
    img.save(out); print("wrote",out)

main()
