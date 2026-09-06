import struct
def getfile(iso_path, want):
    want=want.upper().lstrip("/")
    f=open(iso_path,"rb")
    f.seek(16*2048); pvd=f.read(2048); root=pvd[156:190]
    rlba=struct.unpack("<I",root[2:6])[0]; rlen=struct.unpack("<I",root[10:14])[0]
    def walk(lba,length):
        f.seek(lba*2048); data=f.read(((length+2047)//2048)*2048); i=0; out=[]
        while i<length:
            rl=data[i]
            if rl==0: i=((i//2048)+1)*2048; continue
            rec=data[i:i+rl]; el=struct.unpack("<I",rec[2:6])[0]; sz=struct.unpack("<I",rec[10:14])[0]
            fl=rec[25]; nl=rec[32]; nm=rec[33:33+nl].decode("ascii","replace").split(";")[0]
            if nm not in("\x00","\x01"): out.append((nm.upper(),el,sz,fl))
            i+=rl
        return out
    parts=want.split("/")
    entries=walk(rlba,rlen)
    for depth,p in enumerate(parts):
        match=[e for e in entries if e[0]==p]
        if not match: raise FileNotFoundError(want)
        nm,lba,sz,fl=match[0]
        if depth==len(parts)-1:
            f.seek(lba*2048); d=f.read(sz); f.close(); return d
        entries=walk(lba,sz)
    raise FileNotFoundError(want)
