# -*- coding: utf-8 -*-
"""Fill blocks 65 & 90 blank captions via APPEND (not in-place grow): append the
caption text at the end of the block pool so the record array stays contiguous,
then repoint the clip-257 records' f2 to it. Verifies ALL blocks' routing intact."""
import sys,struct; sys.path.insert(0,"tools"); sys.path.insert(0,sys.argv[1])
import srvc
from srvclib import getfile
from srvc_records import resolve, pool_offsets
from patch import encode
SEC=2048; ORIG_LBA,ORIG_SECTORS=1313214,1618; SEG_LBA=1309609
CUR="iso/srwz_cap.bin"; write="--write" in sys.argv
FIX=[(65,257,"Shinn! Don't charge in!"),(90,257,"I'll mince you with this Drill!")]
def isblank(s): return len(s.replace(b" ",b"").replace(b'"',b""))==0
def setof(BL,seq,bi):
    pool=b"\x00".join(BL[bi].strings)+b"\x00"
    return set(struct.unpack_from("<HH",pool,p) for p,t,a in seq.get(bi,[]))
bin_=getfile(CUR,"/BTL/SRVC.BIN"); seg=srvc.read_seg(getfile(CUR,"/BTL/SRVC.SEG"))
blocks=srvc.parse(bin_,seg); seq,_=resolve(blocks)
before={bi:setof(blocks,seq,bi) for bi in seq}
repoints=[]  # (bi, rec_pos, anchor_slot, new_idx)
for bi,clip,en in FIX:
    blk=blocks[bi]; ps=seg[bi]+len(blk.head)+8*len(blk.ids)
    tgts=[(r,t,a) for r,t,a in seq[bi] if struct.unpack_from("<H",bin_,ps+r)[0]==clip and isblank(blk.strings[t])]
    assert tgts, "no blank clip%d in blk%d"%(clip,bi)
    newidx=len(blk.strings); blk.strings.append(encode('"'+en+'"',"menuhw"))
    for r,t,a in tgts: repoints.append((bi,r,a,newidx))
    print("  blk%d: appended %r, %d record(s) to repoint"%(bi,en[:28],len(tgts)))
nb,nseg=srvc.build(blocks); nb=bytearray(nb)
starts=[struct.unpack("<I",nseg[i*4:i*4+4])[0] for i in range(len(nseg)//4)]
for bi,r,a,newidx in repoints:
    blk=blocks[bi]; on=pool_offsets(blk.strings)
    poolpos=starts[bi]+len(blk.head)+8*len(blk.ids)
    f2=on[newidx]-on[a]; assert 0<=f2<0x10000,"f2 overflow blk%d %d"%(bi,f2)
    nb[poolpos+r+4:poolpos+r+6]=struct.pack("<H",f2)
nb=bytes(nb)
chk=srvc.parse(nb,srvc.read_seg(nseg)); cseq,_=resolve(chk)
bad=[bi for bi in before if setof(chk,cseq,bi)!=before[bi]]
print("blocks with CHANGED routing (must be empty):",bad); assert not bad
# confirm captions filled
for bi,clip,en in FIX:
    pool=b"\x00".join(chk[bi].strings)+b"\x00"
    got=[chk[bi].strings[t] for p,t,a in cseq[bi] if struct.unpack_from("<H",pool,p)[0]==clip and not isblank(chk[bi].strings[t])]
    print("  blk%d clip%d ->"%(bi,clip), repr(got[0].decode("cp932","replace")) if got else "STILL BLANK")
need=(len(nb)+SEC-1)//SEC; print("SRVC %d->%d bytes, %d/%d sectors"%(len(bin_),len(nb),need,ORIG_SECTORS)); assert need<=ORIG_SECTORS
if not write: print("(dry run - routing intact)"); sys.exit(0)
with open(CUR,"r+b") as f:
    f.seek(SEG_LBA*SEC); f.write(nseg+b"\x00"*((-len(nseg))%SEC))
    f.seek(ORIG_LBA*SEC); f.write(nb+b"\x00"*(ORIG_SECTORS*SEC-len(nb)))
    head=bytearray(open(CUR,"rb").read(4*1024*1024)); p=head.find(b"SRVC.BIN;1")
    while p>=0 and head[p-7:p]!=b"\\BTL\\\\": p=head.find(b"SRVC.BIN;1",p+1)
    f.seek(p+0x21); f.write(struct.pack("<I",ORIG_LBA)); f.seek(p+0x25); f.write(struct.pack("<I",ORIG_SECTORS))
    rec=head.find(b"SRVC.BIN;1",0x80000)-33
    f.seek(rec+2); f.write(struct.pack("<I",ORIG_LBA)); f.seek(rec+6); f.write(struct.pack(">I",ORIG_LBA))
    f.seek(rec+10); f.write(struct.pack("<I",len(nb))); f.seek(rec+14); f.write(struct.pack(">I",len(nb)))
print("written")
