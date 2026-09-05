# -*- coding: utf-8 -*-
"""Apply the stage-40 retranslations (rec95, rec99) IN PLACE. Pairs EN<->JP
through the pointer table (export_proofread.pair) so keys match exactly, wraps
each new line to its box, verifies it fits the fixed slot, recompresses serially."""
import sys,json,hashlib,struct; sys.path.insert(0,"tools")
import banlz, reflow_dialogue as R, export_proofread as EP
SEC=2048; LBA,SIZE=1651029,3910128; NL="\n"; KAGI="\u300c"
adv=R.load_adv("iso/srwz_cap.bin"); write="--write" in sys.argv
SPOUT={95:"houkai_jokyoku",99:"impact_again"}
trans={}
for ri,lbl in SPOUT.items():
    trans[ri]=json.load(open("%s/stage40_%s_out.json"%(sys.argv[1],lbl),encoding="utf-8"))

def wrap_field(field, over):
    sp,_,body=field.partition(NL)
    body=body.strip()
    # detect bracket style
    if body[:1]=="\u300c" and body[-1:]=="\u300d": lb,rb,inner="\u300c","\u300d",body[1:-1]
    elif body[:1]=="(" and body[-1:]==")": lb,rb,inner="(",")",body[1:-1]
    elif body[:1]=='"' and body[-1:]=='"': lb,rb,inner='"','"',body[1:-1]
    else: lb,rb,inner="","",body
    inner=inner.replace(NL," ").strip()
    wl=R.reflow(inner,(R.OVERMAP_PX if over else R.SCENE_PX)-21,adv)
    if not wl: wl=[""]
    wl[0]=lb+wl[0]; wl[-1]=wl[-1]+rb
    return (sp+NL+NL.join(wl)) if sp else NL.join(wl), len(wl)

f=open("iso/srwz_cap.bin","r+b" if write else "rb"); f.seek(LBA*SEC); raw=bytearray(f.read(SIZE))
en=[(h,bytearray(d)) for h,d in banlz.decompress_all(bytes(raw)) if isinstance(h,int) and d is not None]
heads=sorted(h for h,_ in en)
fj=open("iso/srwz.bin","rb"); fj.seek(LBA*SEC); jpraw=fj.read(SIZE); fj.close()
jp=[d for h,d in banlz.decompress_all(jpraw) if isinstance(h,int) and d is not None]
applied=0; nofit=[]; touched={}
for ri in SPOUT:
    eb=bytes(en[ri][1]); jb=bytes(jp[ri]); m=EP.pair(eb,jb)
    # keys in offset order (matches export)
    occ={}; key_of={}
    for off in sorted(m):
        et,_=EP.text_at(eb,off)
        if not et or NL not in et: continue
        jt,_=EP.text_at(jb,m[off][0])
        if not jt or KAGI not in jt: continue
        h=hashlib.sha1(jt.encode("cp932","ignore")).hexdigest()[:12]
        n=occ.get(h,0); occ[h]=n+1; key_of[off]="%d:%s:%d"%(ri,h,n)
    d=en[ri][1]; changed=False
    # need box type per offset
    bm=R.boxmap(d)
    for off in sorted(m):
        key=key_of.get(off)
        if not key or key not in trans[ri]: continue
        newfield=trans[ri][key]
        # slot
        z=d.find(b"\x00",off); e=z
        while e<len(d) and d[e]==0: e+=1
        slot=e-off-1
        over=bm.get(off,1)==1
        nf,nl=wrap_field(newfield,over)
        nb=nf.encode("cp932")
        if nb==bytes(d[off:z]): continue
        if len(nb)>slot or nl>3: nofit.append((ri,key,len(nb),slot,nl)); continue
        d[off:off+slot+1]=nb+b"\x00"*(slot+1-len(nb)); changed=True; applied+=1
    if changed: touched[ri]=d
print("applied:",applied,"  did-not-fit:",len(nofit),"  records:",list(touched))
for x in nofit[:10]: print("  NOFIT",x)
if not write: print("(dry run)"); sys.exit(0)
for ri in sorted(touched):
    h=en[ri][0]; nxt=min([x for x in heads if x>h] or [len(raw)]); dd=bytes(touched[ri])
    blob=banlz.compress_record(dd)
    if len(blob)>nxt-h: blob=banlz.compress_record_optimal(dd)
    assert len(blob)<=nxt-h,"rec%d over slot"%ri
    raw[h:h+len(blob)]=blob
    for x in range(h+len(blob),nxt): raw[x]=0
assert [hh for hh,x in banlz.decompress_all(bytes(raw)) if isinstance(hh,int) and x is not None]==heads
f.seek(LBA*SEC); f.write(bytes(raw)); f.close(); print("STAGE written")
