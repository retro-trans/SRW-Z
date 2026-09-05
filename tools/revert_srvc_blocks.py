# -*- coding: utf-8 -*-
"""Revert SRVC blocks 65/90/151/234 to their v0.9.38 (pre fix_blank_captions)
state, to restore correct voice routing. Everything else (reflow, font, other
captions) stays. Writes SRVC.BIN/SEG back in place."""
import sys, struct
sys.path.insert(0, "tools"); sys.path.insert(0, sys.argv[1])
import srvc
from srvclib import getfile
from srvc_records import resolve

SECTOR=2048; ORIG_LBA=1313214; ORIG_SECTORS=1618; SEG_LBA=1309609
CUR="iso/srwz_cap.bin"; GOOD="iso/_v0.9.38.bin"
REVERT=[65,90,151,234]
write="--write" in sys.argv

curbin=getfile(CUR,"/BTL/SRVC.BIN"); curseg=srvc.read_seg(getfile(CUR,"/BTL/SRVC.SEG"))
gdbin =getfile(GOOD,"/BTL/SRVC.BIN"); gdseg=srvc.read_seg(getfile(GOOD,"/BTL/SRVC.SEG"))
cur=srvc.parse(curbin,curseg); gd=srvc.parse(gdbin,gdseg)
assert len(cur)==len(gd)
for bi in REVERT:
    cur[bi]=gd[bi]
nb,nseg=srvc.build(cur)
print("rebuilt SRVC %d -> %d bytes (%+d)"%(len(curbin),len(nb),len(nb)-len(curbin)))
# sanity: re-parse, resolve, and confirm blocks 65/90 seq now match v0.9.38
chk=srvc.parse(nb,srvc.read_seg(nseg))
cseq,_=resolve(chk); gseq,_=resolve(gd)
def cells(BL,seq,bi):
    pool=b"\x00".join(BL[bi].strings)+b"\x00"; s=set()
    for pos,tgt,anc in seq.get(bi,[]):
        s.add(struct.unpack_from("<HH",pool,pos))
    return s
for bi in (65,90,151,234):
    ok = cells(chk,cseq,bi)==cells(gd,gseq,bi)
    print("  block %d seq matches v0.9.38: %s"%(bi,ok))
need=(len(nb)+SECTOR-1)//SECTOR
print("need %d sectors (budget %d)"%(need,ORIG_SECTORS)); assert need<=ORIG_SECTORS
if not write:
    print("(dry run)"); sys.exit(0)
with open(CUR,"r+b") as f:
    f.seek(SEG_LBA*SECTOR); f.write(nseg+b"\x00"*((-len(nseg))%SECTOR))
    f.seek(ORIG_LBA*SECTOR); f.write(nb+b"\x00"*(ORIG_SECTORS*SECTOR-len(nb)))
    head=bytearray(open(CUR,"rb").read(4*1024*1024))
    p=head.find(b"SRVC.BIN;1")
    while p>=0 and head[p-7:p]!=b"\\BTL\\\\": p=head.find(b"SRVC.BIN;1",p+1)
    f.seek(p+0x21); f.write(struct.pack("<I",ORIG_LBA))
    f.seek(p+0x25); f.write(struct.pack("<I",ORIG_SECTORS))
    rec=head.find(b"SRVC.BIN;1",0x80000)-33
    f.seek(rec+2);  f.write(struct.pack("<I",ORIG_LBA))
    f.seek(rec+6);  f.write(struct.pack(">I",ORIG_LBA))
    f.seek(rec+10); f.write(struct.pack("<I",len(nb)))
    f.seek(rec+14); f.write(struct.pack(">I",len(nb)))
print("written")
