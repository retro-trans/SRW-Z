"""Add release identification to the native title-screen background.

Works on either edition. Only VT1 bank 6's bright 640x448 background pixels
change; its palette, the other title assets, code and captions are preserved.
Default is a dry run. Builds always start from the verified unbranded bank,
so changing the version requires a clean base rather than painting over text.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import banlz
import banlz_strict

LO, HI = 0xA751B0, 0xAE7710
TIM = 0x1B10D0
NATIVE_SHA256 = 'a7798be839a72416d358b7f3f2e0ae9d95c866cd4226ba6d8305a14ca8a3559a'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paint(record, version, author, font):
    if digest(record) != NATIVE_SHA256:
        raise ValueError('Title bank differs from the verified unbranded image')
    out = bytearray(record)
    header = struct.unpack_from('<IIIHHBBBBHH', record, TIM+16)
    total, cs, size, hs, colors, pf, mm, ct, kind, w, h = header
    if (size,hs,colors,kind,w,h)!=(286720,48,256,5,640,448):
        raise ValueError('Unexpected title background format')
    pix=TIM+16+hs; clut=pix+size
    order=[(i&0xE7)|((i&8)<<1)|((i&16)>>1) for i in range(256)]
    pal=[tuple(record[clut+4*i:clut+4*i+4]) for i in order]
    opaque=[i for i,p in enumerate(pal) if p[3]>=0x80]
    if not opaque:raise ValueError('Background has no opaque palette entries')
    white=min(opaque,key=lambda i:sum((v-255)**2 for v in pal[i][:3]))
    dark=min(opaque,key=lambda i:sum(v*v for v in pal[i][:3]))
    face=ImageFont.truetype(str(font),12)
    shadow=Image.new('1',(w,h));ink=Image.new('1',(w,h))
    sd,idraw=ImageDraw.Draw(shadow),ImageDraw.Draw(ink)
    boxes=[]
    for text,top in [(version,402),(author,420)]:
        box=idraw.textbbox((0,0),text,font=face)
        width,height=box[2]-box[0],box[3]-box[1]
        if width>220 or height>15:raise ValueError('Release label exceeds reserved corner')
        x=w-18-width;y=top-box[1]
        sd.text((x,y),text,font=face,fill=1,stroke_width=1,stroke_fill=1)
        idraw.text((x,y),text,font=face,fill=1)
        boxes.append(dict(text=text,box=[x,top,x+width,top+height]))
    sm,im=shadow.load(),ink.load();changed=[]
    for y in range(h):
        for x in range(w):
            if sm[x,y]:
                pos=pix+y*w+x;out[pos]=white if im[x,y] else dark
                if out[pos]!=record[pos]:changed.append(pos)
    if not changed:raise ValueError('Labels changed no pixels')
    if any(not (pix<=p<pix+size) for p in changed):raise ValueError('Non-pixel change')
    preview=Image.new('RGB',(w,h));preview.putdata([pal[i][:3] for i in out[pix:pix+size]])
    return bytes(out),preview,dict(labels=boxes,changed_pixels=len(changed),palette_unchanged=True,
        native_record_sha256=NATIVE_SHA256,record_sha256=digest(out),font_sha256=digest(font.read_bytes()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('iso',type=Path);p.add_argument('--version',default='v0.9.79')
    p.add_argument('--author',default='github.com/retro-trans')
    p.add_argument('--font',type=Path,default=Path(r'C:\Windows\Fonts\arialbd.ttf'))
    p.add_argument('--compressor',type=Path,help='Optional compiled banlz_pack_fast executable')
    p.add_argument('--work',type=Path,required=True);p.add_argument('--write',action='store_true')
    args=p.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+',args.version):p.error('Invalid version')
    # Reuse the public edition-aware ISO parser, not a hardcoded disc LBA.
    sys.path.insert(0,str(Path(__file__).resolve().parent/'best_adapter'))
    from disc import Disc
    disc=Disc(args.iso);entry=disc.entries['DATA/VT1.BIN'];offset=entry['lba']*2048+LO
    with args.iso.open('rb') as f:f.seek(offset);raw=f.read(HI-LO)
    record,end=banlz.decompress_record(raw)
    painted,preview,report=paint(bytes(record),args.version,args.author,args.font)
    args.work.mkdir(parents=True,exist_ok=True)
    preview.save(args.work/'title-background.png')
    cache=args.work/('bank6-'+digest(painted)+'.bin')
    if cache.exists():blob=cache.read_bytes()
    else:
        print('Compressing title bank',flush=True)
        if args.compressor:
            plain=args.work/'bank6-painted.bin';plain.write_bytes(painted)
            subprocess.run([str(args.compressor.resolve()),str(plain.resolve()),str(cache.resolve()),'96','optimal'],check=True)
            blob=cache.read_bytes()
        else:
            blob=banlz.compress_record(painted,flags=29)
            if len(blob)>len(raw):blob=banlz.compress_record_optimal(painted,flags=29)
        cache.write_bytes(blob)
    total,flags,start=banlz.parse_header(blob)
    strict,issues=banlz_strict.verify(blob,start,total)
    if issues or strict!=painted:raise ValueError('Strict game decoder check failed')
    if len(blob)>len(raw):raise ValueError('Title bank exceeds its native slot: %d > %d'%(len(blob),len(raw)))
    report.update(iso=str(args.iso.resolve()),file='DATA/VT1.BIN',bank=6,
        offset=offset,compressed_bytes=len(blob),capacity=len(raw),strict_decoder=True,written=args.write)
    print(json.dumps(report,indent=2),flush=True)
    replacement=blob+bytes(len(raw)-len(blob))
    if args.write:
        with args.iso.open('r+b') as f:
            f.seek(offset);f.write(replacement);f.flush();f.seek(offset)
            if f.read(len(raw))!=replacement:raise ValueError('Disc readback failed')
    (args.work/('report-'+('best' if 'SLPS_732.70' in disc.entries else 'original')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
