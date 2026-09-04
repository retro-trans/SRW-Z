# -*- coding: utf-8 -*-
"""In-place fix: block 324 caption 「斗牙様…」 shipped as "..." -> "Touga".
Free-mode slot is 8 bytes; "Touga" quoted = 7 bytes + 1 space filler."""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SEC=2048
POOL_OFF = 2692383     # byte offset within SRVC.BIN of the "..." slot (entry 193, block 324)
OLD = b'"\x85@\x85@\x85@"'          # shipped "..." in menuhw (8 bytes)
NEW = b'"Touga" '                    # 7 bytes + 1 space filler = 8 bytes, null unchanged

def srvc_lba(path):
    f=open(path,"rb"); f.seek(16*SEC); pvd=f.read(SEC)
    rl=struct.unpack_from("<I",pvd,158)[0]; rn=struct.unpack_from("<I",pvd,166)[0]
    def walk(lba,length,pre=""):
        f.seek(lba*SEC); d=f.read(((length+SEC-1)//SEC)*SEC); i=0
        while i<len(d):
            r=d[i]
            if r==0:
                i=(i//SEC+1)*SEC
                if i>=len(d): return None
                continue
            nl=d[i+32]; nm=d[i+33:i+33+nl]
            if nm not in (b"\x00",b"\x01"):
                nm2=nm.split(b";")[0]; ex=struct.unpack_from("<I",d,i+2)[0]; sz=struct.unpack_from("<I",d,i+10)[0]
                full=pre+"/"+nm2.decode()
                if d[i+25]&2:
                    r2=walk(ex,sz,full)
                    if r2: return r2
                elif full=="/BTL/SRVC.BIN":
                    return ex,sz
            i+=r
        return None
    hit=walk(rl,rn); f.close(); return hit

def main():
    iso=sys.argv[1]; write="--write" in sys.argv
    lba,sz=srvc_lba(iso)
    abs_off=lba*SEC+POOL_OFF
    print("SRVC.BIN LBA=%d size=%d -> abs offset %d" % (lba,sz,abs_off))
    f=open(iso,"r+b" if write else "rb")
    f.seek(abs_off); cur=f.read(9)   # 8 slot + 1 null
    print("current 9 bytes: %r" % cur)
    if cur[:8]==NEW[:8] and cur[8:9]==b"\x00":
        print("already patched."); f.close(); return
    assert cur[:8]==OLD, "slot mismatch: have %r want %r" % (cur[:8],OLD)
    assert cur[8:9]==b"\x00", "no null terminator after slot"
    assert len(NEW)==8
    if not write:
        print("would write %r (dry run)" % NEW); f.close(); return
    f.seek(abs_off); f.write(NEW)
    f.seek(abs_off); print("verify: %r" % f.read(9))
    f.close(); print("PATCHED: 斗牙様… caption now shows \"Touga\" (was \"...\")")

main()
