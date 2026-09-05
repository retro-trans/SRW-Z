# -*- coding: utf-8 -*-
"""Fix truncated battle-dialogue fragments (orphan trailing quote). Two kinds:
  * parenthetical inner monologue "(...)" - already complete on disc, just drop
    the stray closing quote (source duplicates the speaker, so don't use it).
  * head-truncated dialogue - restore the full line from english_script.json.
All IN PLACE (slots kept the original size), re-wrapped to the over-map box; only
those that fit are written, the rest reported for rewording. Recompress + gate."""
import sys,json,os; sys.path.insert(0,"tools")
from concurrent.futures import ProcessPoolExecutor
import banlz, reflow_dialogue as R
SEC=2048; LBA,SIZE=1651029,3910128
es=json.load(open('analysis/english_script.json',encoding='utf-8'))["rows"]
esmap=dict(((r["rec"],r["off"]),r["en"]) for r in es)
adv=R.load_adv("iso/srwz_cap.bin"); BS=chr(92)
write="--write" in sys.argv
f=open("iso/srwz_cap.bin","r+b" if write else "rb"); f.seek(LBA*SEC); raw=bytearray(f.read(SIZE))
live=[(h,bytearray(d)) for h,d in banlz.decompress_all(bytes(raw)) if isinstance(h,int) and d is not None]
heads=sorted(h for h,_ in live)
touched={}; done=0; toolong=[]; paren=0; samples=[]
for ri,(h,d) in enumerate(live):
    changed=False; i=0
    while i<len(d):
        z=d.find(b"\x00",i)
        if z<0: break
        e=z
        while e<len(d) and d[e]==0: e+=1
        slot=e-i-1
        try: disc=d[i:z].decode("cp932")
        except: disc=None
        if disc and "\n" in disc:
            sp,_,body=disc.partition("\n")
            if body.rstrip().endswith('"') and body.count('"')==1 and "\u300c" not in body and len(sp)<20 and BS not in body and "$" not in body and (ri,i) in esmap:
                if body.lstrip().startswith("("):
                    inner=body.rstrip()[:-1].replace("\n"," ").strip()   # drop orphan quote
                    quoted=False
                else:
                    src=esmap[(ri,i)].strip()
                    if src.startswith('"'): src=src[1:]
                    if src.endswith('"'): src=src[:-1]
                    inner=src.replace("\n"," ").strip(); quoted=True
                wl=R.reflow(inner, R.OVERMAP_PX-21, adv)
                if wl and len(wl)<=3:
                    nb=("\n".join(wl)); nb=('"'+nb+'"') if quoted else nb
                    field=(sp+"\n"+nb).encode("cp932")
                    if len(field)<=slot:
                        if field!=d[i:z]:
                            d[i:i+slot+1]=field+b"\x00"*(slot+1-len(field)); changed=True; done+=1
                            if body.lstrip().startswith("("): paren+=1
                            if len(samples)<12: samples.append((ri,disc.replace("\n"," / "),(sp+"\n"+nb).replace("\n"," / ")))
                    else: toolong.append((ri,sp,inner[:40]))
                else: toolong.append((ri,sp,inner[:40]))
        i=z+1
    if changed: touched[ri]=d
print("fixed:",done,"(of which paren-quote-strip:",paren,")   too long/reword:",len(toolong),"  records:",len(touched))
for ri,o,n in samples:
    print("  rec%d"%ri); print("    OLD:",repr(o)); print("    NEW:",repr(n))
if not write:
    print("(dry run)"); sys.exit(0)
def _c(job):
    ri,room,dat=job; b=banlz.compress_record(dat)
    if len(b)>room: b=banlz.compress_record_optimal(dat)
    return ri,b
jobs=[]
for ri in sorted(touched):
    h=live[ri][0]; nxt=min([x for x in heads if x>h] or [len(raw)]); jobs.append((ri,h,nxt,bytes(touched[ri])))
got={}
for r,h,n,dd in jobs: got[r]=_c((r,n-h,dd))[1]
for ri,h,nxt,dd in jobs:
    b=got[ri]; assert len(b)<=nxt-h,"rec%d over"%ri; raw[h:h+len(b)]=b
    for x in range(h+len(b),nxt): raw[x]=0
assert [hh for hh,x in banlz.decompress_all(bytes(raw)) if isinstance(hh,int) and x is not None]==heads
f.seek(LBA*SEC); f.write(bytes(raw)); f.close(); print("STAGE written")
