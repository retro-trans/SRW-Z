# -*- coding: utf-8 -*-
"""DATA HELP spirit legend: drop the explanatory header row so all 4 command
rows (17 spirits) fit the 4-row box. Non-final lines stay even (row-count parity)."""
import sys; sys.path.insert(0,"tools"); import banlz
SEC=2048; COMP_LBA,COMP_NSEC=1823000,74; OFF=0x722A0
write="--write" in sys.argv
f=open("iso/srwz_cap.bin","r+b" if write else "rb"); f.seek(COMP_LBA*SEC)
raw=bytearray(f.read(COMP_NSEC*SEC))
live=[(h,d) for h,d in banlz.decompress_all(bytes(raw)) if isinstance(h,int) and d is not None]
hdr,data=live[0][0],bytearray(live[0][1])
z=data.index(b"\x00",OFF); e=z
while e<len(data) and data[e]==0: e+=1
slot=e-OFF-1; old=bytes(data[OFF:z])
lines=old.split(b"\x0a")
assert lines[0].startswith(b"Spirit commands"), "header not where expected: %r"%lines[0][:20]
cmd=lines[1:]                                 # drop the header row
# parity: pad any odd non-final line to even (trailing space, invisible)
def rows_seen(s):
    i=0;n=1
    while i<len(s):
        if s[i]==0x0a:n+=1;i+=1
        else:i+=2
    return n
fixed=[]
for i,ln in enumerate(cmd):
    if i<len(cmd)-1 and len(ln)%2==1: ln=ln+b"\x20"
    fixed.append(ln)
new=b"\x0a".join(fixed)
assert len(new)<=slot
print("OLD %d rows -> NEW %d rows; counter sees %d; bytes %d->%d"%(
    len(lines),len(fixed),rows_seen(new),len(old),len(new)))
for ln in fixed: print("   (%2dB) %r"%(len(ln),ln.decode("cp932","replace")))
if not write:
    print("(dry run)"); sys.exit(0)
data[OFF:OFF+slot+1]=new+b"\x00"*(slot+1-len(new))
blob=banlz.compress_record(bytes(data))
if len(blob)>COMP_NSEC*SEC: blob=banlz.compress_record_optimal(bytes(data))
assert hdr+len(blob)<=COMP_NSEC*SEC
raw[hdr:hdr+len(blob)]=blob
for x in range(hdr+len(blob),COMP_NSEC*SEC): raw[x]=0
f.seek(COMP_LBA*SEC); f.write(bytes(raw)); f.close()
print("COMPDATA written (%d B)"%len(blob))
