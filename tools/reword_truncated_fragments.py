# -*- coding: utf-8 -*-
"""Reword the too-long truncated fragments into complete short lines that fit
their slots. Faithful to english_script source; skips false positives (title
cards, debug lines) and tiny slots that can't hold a complete sentence."""
import sys; sys.path.insert(0,"tools"); import banlz, reflow_dialogue as R
SEC=2048; LBA,SIZE=1651029,3910128
adv=R.load_adv("iso/srwz_cap.bin"); write="--write" in sys.argv
# (rec, off) -> reworded inner body (no quotes). Faithful short forms.
REW={
 (132,0x154a0):"Your end is here!",
 (132,0x156e0):"Fight on and I'll crush your spirit!",
 (144,0x1eb30):"The more serious you get, the sillier you look!",
 (144,0x1eb90):"Entertain me! Be my punchline!",
 (144,0x1ebf0):"I liked your hot blood, but you're too cocky.",
 (144,0x1ec60):"God or devil - I like that line.",
 (144,0x1ee20):"I hate those who mock hard work!",
 (144,0x1ef90):"That's nonsense!",
 (144,0x1f200):"No more games!",
 (144,0x1f250):"We'll stop you here!",
 (144,0x1f2b0):"Justice doesn't always win! Let me teach you!",
 (144,0x1f380):"I'm always dead earnest.",
 (144,0x1f490):"I aim to be the Demon King!",
 (144,0x20420):"Wipe off that smirk!",
 (144,0x20470):"No taste for boring attacks.",
 (144,0x206c0):"Whatever world it is, I love its people.",
 (144,0x20800):"I'll see tomorrow!",
 (144,0x22540):"I accept no one but me!",
 (144,0x226d0):"I'll go my own way!",
 (144,0x22840):"Their struggle was a jolt for the world.",
}
f=open("iso/srwz_cap.bin","r+b" if write else "rb"); f.seek(LBA*SEC); raw=bytearray(f.read(SIZE))
live=[(h,bytearray(d)) for h,d in banlz.decompress_all(bytes(raw)) if isinstance(h,int) and d is not None]
heads=sorted(h for h,_ in live)
touched={}; done=0; nofit=[]
for ri,(h,d) in enumerate(live):
    changed=False
    for (rr,off),inner in REW.items():
        if rr!=ri: continue
        z=d.find(b"\x00",off)
        if z<0: continue
        e=z
        while e<len(d) and d[e]==0: e+=1
        slot=e-off-1
        disc=d[off:z].decode("cp932","replace"); sp=disc.split("\n",1)[0]
        wl=R.reflow(inner, R.OVERMAP_PX-21, adv)
        field=(sp+"\n"+'"'+"\n".join(wl)+'"').encode("cp932")
        if len(wl)<=3 and len(field)<=slot:
            d[off:off+slot+1]=field+b"\x00"*(slot+1-len(field)); changed=True; done+=1
            print("  rec%d %-10s -> %r"%(ri,sp,'"'+" ".join(wl)+'"'))
        else:
            nofit.append((ri,off,sp,len(field),slot))
    if changed: touched[ri]=d
print("reworded:",done,"  didn't fit:",len(nofit))
for ri,off,sp,fl,sl in nofit: print("  NOFIT rec%d @%#x %s (%dB > %dB)"%(ri,off,sp,fl,sl))
if not write:
    print("(dry run)"); sys.exit(0)
def _c(ri,room,dat):
    b=banlz.compress_record(dat)
    if len(b)>room: b=banlz.compress_record_optimal(dat)
    return b
for ri in sorted(touched):
    h=live[ri][0]; nxt=min([x for x in heads if x>h] or [len(raw)])
    b=_c(ri,nxt-h,bytes(touched[ri])); assert len(b)<=nxt-h
    raw[h:h+len(b)]=b
    for x in range(h+len(b),nxt): raw[x]=0
assert [hh for hh,x in banlz.decompress_all(bytes(raw)) if isinstance(hh,int) and x is not None]==heads
f.seek(LBA*SEC); f.write(bytes(raw)); f.close(); print("STAGE written")
