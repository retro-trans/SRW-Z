# -*- coding: utf-8 -*-
"""Rewrap the female-protagonist select bio (COMPDATA 0x7A800) from 4 lines to 3
so the box stops clipping 'she has.'. Byte-level: only \n positions change, every
character is preserved, so no re-encode and byte count can't grow."""
import sys; sys.path.insert(0,"tools"); import banlz
SEC=2048; COMP_LBA,COMP_NSEC=1823000,74; OFF=0x7a800
write="--write" in sys.argv
f=open("iso/srwz_cap.bin","r+b" if write else "rb"); f.seek(COMP_LBA*SEC)
raw=bytearray(f.read(COMP_NSEC*SEC))
live=[(h,d) for h,d in banlz.decompress_all(bytes(raw)) if isinstance(h,int) and d is not None]
hdr,data=live[0][0],bytearray(live[0][1])
z=data.index(b"\x00",OFF); e=z
while e<len(data) and data[e]==0: e+=1
slot=e-OFF-1; old=bytes(data[OFF:z])
flat=old.replace(b"\x0a",b"\x20")            # one flow
words=flat.split(b"\x20")
assert b"".join(old.split()) == b"".join(flat.split()), "word content changed"
# 3-line regroup (word indices), keeps 'earnest -' at L1 end, 'she gives...' at L2
L0=b" ".join(words[0:10])
L1=b" ".join(words[10:18])
L2=b" ".join(words[18:25])
new=b"\x0a".join([L0,L1,L2])
# integrity: same characters, just \n<->space moved
assert b"".join(new.split())==b"".join(old.split()), "content changed!"
assert len(new)<=slot, "new %d > slot %d"%(len(new),slot)
print("OLD (%d B, %d lines):"%(len(old),old.count(0x0a)+1))
for l in old.split(b"\x0a"): print("   %r"%l.decode("cp932","replace"))
print("NEW (%d B, %d lines):"%(len(new),new.count(0x0a)+1))
for l in new.split(b"\x0a"): print("   (%2d) %r"%(len(l),l.decode("cp932","replace")))
if not write:
    print("(dry run)"); sys.exit(0)
data[OFF:OFF+slot+1]=new+b"\x00"*(slot+1-len(new))
blob=banlz.compress_record(bytes(data))
if len(blob)>COMP_NSEC*SEC: blob=banlz.compress_record_optimal(bytes(data))
assert hdr+len(blob)<=COMP_NSEC*SEC
raw[hdr:hdr+len(blob)]=blob
for x in range(hdr+len(blob),COMP_NSEC*SEC): raw[x]=0
f.seek(COMP_LBA*SEC); f.write(bytes(raw)); f.close()
print("COMPDATA written (%d B compressed)"%len(blob))
