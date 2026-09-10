"""Merge data archives with explicit handling of Best's official corrections."""
import json
import struct
import sys
from pathlib import Path
from disc import dump,sha


def u32(b,p):return struct.unpack_from('<I',b,p)[0]


def compdata(a,b,c,encode):
    if not len(a)==len(b)==len(c)==524032:raise ValueError('COMPDATA size drift')
    out=bytearray(c);handled=set(range(0x80,0x8C0));pointers=[]
    out[0x80:0x8C0]=b[0x80:0x8C0]
    for p in range(0,len(a)-3,4):
        if p in handled:continue
        x,y,z=[u32(d,p) for d in (a,b,c)]
        if x!=y and y-x==0x800 and 0x100000<=x<0x2000000:
            if not 0x100000<=z<0x2000000:raise ValueError('COMPDATA English pointer type changed at %#x'%p)
            struct.pack_into('<I',out,p,z+0x800);handled.update(range(p,p+4));pointers.append(p)
    fields=[(0x7165,1,1,0),(0x59F9E,2,315,316),(0x5B02E,2,254,252),(0x5D4FF,1,18,17)]
    for p,width,old,new in fields:
        if int.from_bytes(a[p:p+width],'little')!=old or int.from_bytes(b[p:p+width],'little')!=new:
            raise ValueError('COMPDATA official correction preimage changed')
        out[p:p+width]=b[p:p+width];handled.update(range(p,p+width))
    for p in (0x244CE,0x2457E):
        if b[p:b.find(b'\0',p)].decode('cp932')!='エゥーゴ兵':raise ValueError('Best faction preimage drift')
        payload=encode('AEUG Soldier','menu')+b'\0'
        out[p:p+14]=payload+bytes(14-len(payload));handled.update(range(p,p+14))
    texts={0x6C4C0:'Nullifies damage of 2000 or less.\nRequires Will 100 and costs 5 EN.\nIn Center Formation, covers the squad.',
           0x6C550:None}
    corrected=[]
    for original,text in texts.items():
        owners=[p for p in pointers if u32(a,p)==0x6D6800+original]
        if len(owners)!=1:raise ValueError('COMPDATA corrected description owner drift')
        dst=u32(c,owners[0])-0x6D6800;end=c.find(b'\0',dst)
        if text is None:
            before=c[dst:end]
            old=encode('Costs 10 EN','menu');new=encode('Costs 5 EN','menu')
            if before.count(old)==1:payload=before.replace(old,new)+b'\0'
            elif before.count(new)==1:payload=before+b'\0'
            else:raise ValueError('Barrier Field English description changed; review correction')
        else:payload=encode(text,'menu')+b'\0'
        room=end+1-dst
        if len(payload)>room:raise ValueError('Best description exceeds English allocation')
        out[dst:end+1]=payload+bytes(room-len(payload))
        corrected.append(dict(owner=hex(owners[0]),target=hex(dst),bytes=len(payload),capacity=room))
    # These are native text edits, now represented by the relocated owners above.
    handled.update(range(0x6C4C0,0x6C5C0))
    unknown=[hex(p) for p,(x,y) in enumerate(zip(a,b)) if x!=y and p not in handled]
    if unknown:raise ValueError('Unknown COMPDATA native changes: '+str(unknown[:16]))
    for p in pointers:
        if u32(out,p)!=u32(c,p)+0x800:raise ValueError('COMPDATA pointer readback failed')
    return bytes(out),dict(pointers=len(pointers),corrected_descriptions=corrected,official_fields=4)


def encyclopedia(a,b,c,zkn,index):
    parsed=[zkn.parse(zkn.payload_of(d)) for d in (a,b,c)]
    if len({v[:3] for v in parsed})!=1:raise ValueError('ZKAN header drift')
    fields=[[row for row in v[3] if row[0] not in ('DSIZ','DATA')] for v in parsed]
    if not [r[0] for r in fields[0]]==[r[0] for r in fields[1]]==[r[0] for r in fields[2]]:
        raise ValueError('ZKAN field identity drift')
    records=bytearray();expected=[]
    for ar,br,cr in zip(*fields):
        tag,_,old=ar;native=br[2];text=cr[2]
        if old!=native and tag not in ('VOIC','ACTR'):raise ValueError('Unknown ZKAN native edit')
        if tag=='VOIC':text=native
        elif tag=='ACTR' and old!=native:
            names={'千葉一伸':'Kazunobu Chiba','松本吉朗':'Yoshiro Matsumoto'}
            actor=native.decode('cp932')
            if actor not in names:raise ValueError('Unknown Best voice actor correction')
            text=names[actor].encode('ascii')
        records.extend(tag.encode('ascii')+struct.pack('<I',len(text))+text)
        expected.append((tag,text))
    magic,kind,version,_=parsed[2]
    payload=magic.encode()+kind.encode()+struct.pack('<II',version,12)
    payload+=b'DSIZ'+struct.pack('<I',len(records)+8)+b'DATA'+struct.pack('<I',len(records))+records
    payload+=bytes((-len(payload))%16)
    out=struct.pack('<8I',1,32,0,len(payload),len(payload),0,0,0)+zkn.obf(payload)
    actual=[(t,d) for t,p,d in zkn.parse(zkn.payload_of(out))[3] if t not in ('DSIZ','DATA')]
    if actual!=expected:raise ValueError('ZKAN readback failed')
    return out


def help_book(a,b,c,parser):
    if a[:0xEB70]!=b[:0xEB70] or a[0xEB70+2064:]!=b[0xEB70+2064:]:raise ValueError('Unknown Best help changes')
    aa,_=parser.parse(a);bb,_=parser.parse(b);cc,_=parser.parse(c)
    section=next(s.index for s in aa if s.off==0xEB70)
    page=cc[section]
    # Stable authored positions identify the two costs even after English repack.
    hits=0
    for r in page.runs:
        if r.x==247 and r.y==234 and 'Costs' in r.text:
            if r.text not in ('by １０００． Costs ５','by １０００． Costs １０'):raise ValueError('I-Field wording needs review')
            r.text='by １０００． Costs １０';hits+=1
        if r.x==247 and r.y==289 and 'Costs' in r.text:
            if r.text not in ('Costs １０ EN．','Costs ５ EN．'):raise ValueError('Barrier Field wording needs review')
            r.text='Costs ５ EN．';hits+=1
    if hits!=2:raise ValueError('Best Q&A correction bindings changed')
    out=parser.build(c,[page])
    actual=parser.parse(out)[0][section]
    if actual.text()!=page.text():raise ValueError('Q&A readback mismatch')
    return out


def run(root,tools_dir):
    root=Path(root);sys.path.insert(0,str(tools_dir))
    import zkn,nisv_rec6
    from patch import encode
    report=[]
    for name,n in [('DATA/COMPDATA.BN',1),('DATA/HSFC.BIN',4),('DATA/NISVDATA.BIN',7),('DATA/MTVZKNPT.BIN',411)]:
        for i in range(n):
            a,b,c=[(root/'decoded'/v/name/('%03d.bin'%i)).read_bytes() for v in ('original','best','english')]
            proof={}
            if name=='DATA/COMPDATA.BN':out,proof=compdata(a,b,c,encode)
            elif a==b:out=c
            elif a==c:out=b
            elif name=='DATA/NISVDATA.BIN' and i==6:out=help_book(a,b,c,nisv_rec6)
            elif name=='DATA/MTVZKNPT.BIN':out=encyclopedia(a,b,c,zkn,i)
            else:raise ValueError('Unhandled native change: %s/%d'%(name,i))
            p=root/'decoded/output'/name/('%03d.bin'%i);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(out)
            report.append(dict(member=name,index=i,bytes=len(out),sha256=sha(out),details=proof))
        print(name,n,'merged',flush=True)
    dump(root/'data-port.json',report)


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
