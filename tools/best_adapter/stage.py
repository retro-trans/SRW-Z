"""Merge English text edits into Best-native scenario containers."""
import json
import struct
import sys
from pathlib import Path
from disc import dump, sha

BASE=0x7566F0
BEST=BASE+0x800


def u32(data,off):return struct.unpack_from('<I',data,off)[0]


def owned_texts(data,F,S):
    # The legacy map accepts three-byte ASCII pointer words as text. That can
    # hide a real dialogue owner (e.g. record 139's Pierre line at 0x9990).
    candidates={};mask=bytearray(len(data))
    for p in range(0,len(data)-3,4):
        if p in (0x0C,0x28,0x2C):continue
        t=u32(data,p)-BASE
        text=F.text_at(data,t) if 0<=t<len(data) else None
        short_jp=text is not None and len(text)==2 and 0x81<=text[0]<=0x9F and 0x40<=text[1]<=0xFC and F.is_text(text)
        short_ascii=text is not None and text.isalpha() and len(text)<=5
        if text and (S.is_real_text(text) or short_jp or short_ascii):
            candidates.setdefault(t,[]).append(p)
            n=len(F.text_at(data,t))+1;mask[t:t+n]=b'\1'*n
    return {t:[p for p in ps if not mask[p]] for t,ps in candidates.items() if any(not mask[p] for p in ps)}


def translated_texts(a,c,F,S):
    result={}
    for ps in owned_texts(a,F,S).values():
        for p in ps:
            t=u32(c,p)-BASE
            if 0<=t<len(c) and F.is_text(F.text_at(c,t)):
                result.setdefault(t,[]).append(p)
    return result


def safe_text(data,F,S):
    starts=sorted(owned_texts(data,F,S));mask=bytearray(len(data))
    for t in starts:
        end=t+len(F.text_at(data,t))+1;mask[t:end]=b'\1'*(end-t)
        q=end
        while q<len(data) and not data[q]:q+=1
        if q in starts:mask[end:q]=b'\1'*(q-end)
    return mask


def fit_native(a,c,F,S):
    """Repack grown English pools into proven native text space, losslessly."""
    if len(c)<=len(a):return c,0
    mask=safe_text(a,F,S);gaps=[];p=0
    while p<len(mask):
        if not mask[p]:p+=1;continue
        q=p+1
        while q<len(mask) and mask[q]:q+=1
        gaps.append([p,q]);p=q
    pm=translated_texts(a,c,F,S)
    tops=[];parent={}
    for t in sorted(pm):
        if tops and t<=tops[-1]+len(F.text_at(c,tops[-1])):parent[t]=tops[-1]
        else:tops.append(t);parent[t]=t
    before={p:F.text_at(c,t) for t,ps in pm.items() for p in ps}
    out=bytearray(c[:len(a)])
    for lo,hi in gaps:out[lo:hi]=bytes(hi-lo)
    dest={}
    for t in sorted(tops,key=lambda t:(-len(F.text_at(c,t)),t)):
        payload=F.text_at(c,t)+b'\0'
        available=[g for g in gaps if g[1]-g[0]>=len(payload)]
        if not available:raise ValueError('English text cannot fit native scenario allocation without editing')
        g=min(available,key=lambda g:(g[1]-g[0],g[0]))
        dest[t]=g[0];out[g[0]:g[0]+len(payload)]=payload;g[0]+=len(payload)
    for t,ps in pm.items():
        target=dest[parent[t]]+t-parent[t]
        for p in ps:struct.pack_into('<I',out,p,BASE+target)
    for p,text in before.items():
        if F.text_at(out,u32(out,p)-BASE)!=text:raise ValueError('Scenario compaction changed a referenced string')
    # No overlooked aligned owner may still point into the discarded tail.
    text_mask=bytearray(len(c))
    for t in tops:text_mask[t:t+len(F.text_at(c,t))+1]=b'\1'*(len(F.text_at(c,t))+1)
    for p in range(0,len(a)-3,4):
        if p in (0x0C,0x28,0x2C) or any(text_mask[p:p+4]):continue
        if BASE+len(a)<=u32(c,p)<BASE+len(c) and p not in before:
            raise ValueError('Unclassified pointer into discarded scenario tail at %#x'%p)
    return bytes(out),len(tops)


def shifted_names_record(a,b,c,F,S):
    """Record 161 keeps its six name owners in place but moves text by 0x80."""
    if (len(a),len(b),len(c)) != (4752,4880,4752):
        raise ValueError('STAGE 161 allocation changed')
    expected={0x1190:0x62C,0x11B8:0x64C,0x11C8:0x66C,
              0x11E0:0x68C,0x11F8:0x6AC,0x11A8:0x6CC}
    if owned_texts(a,F,S)!={t:[p] for t,p in expected.items()}:
        raise ValueError('STAGE 161 owner map changed')
    out=bytearray(b);allowed=bytearray(len(a));checks=[]
    for src,owner in expected.items():
        dst=src+0x80
        if u32(c,owner)!=BASE+src or u32(b,owner)!=BEST+dst:
            raise ValueError('STAGE 161 name owner changed')
        jp=F.text_at(a,src)
        if F.text_at(b,dst)!=jp:
            raise ValueError('STAGE 161 native name changed')
        stop=src+len(jp)+1
        while stop<len(a) and a[stop]==0:stop+=1
        native_stop=dst+len(jp)+1
        while native_stop<len(b) and b[native_stop]==0:native_stop+=1
        allowed[src:stop]=b'\1'*(stop-src)
        text=F.text_at(c,src)
        if text is None or len(text)+1>min(stop-src,native_stop-dst):
            raise ValueError('STAGE 161 translated name exceeds native slot')
        out[dst:native_stop]=text+b'\0'+bytes(native_stop-dst-len(text)-1)
        checks.append((owner,text))
    if any(x!=z and not allowed[p] for p,(x,z) in enumerate(zip(a,c))):
        raise ValueError('STAGE 161 has edits outside audited name slots')
    for owner,text in checks:
        if F.text_at(out,u32(out,owner)-BEST)!=text:
            raise ValueError('STAGE 161 name readback failed')
    return bytes(out),dict(index=161,owners=len(checks),bytes=len(out),
        source_bytes=len(c),official_layout_growth=128,sha256=sha(out),
        corrections=[],compacted_texts=0,audited_name_owners=list(expected.values()))


def build_record(index,a,b,c,helpers):
    F,S=helpers
    source_bytes=len(c)
    c,compacted=fit_native(a,c,F,S)
    def shift(o):
        if index==26:return 128
        if index==161:return 96 if o<4400 else 128
        return 0
    if a==c:return b,dict(index=index,unchanged_english=True,owners=0)
    if index==161:
        return shifted_names_record(a,b,c,F,S)
    native=b
    if index in (111,150):
        # Best shortened a shared text tail. Restore the English allocation;
        # preserve native scenario instructions and rebase every tail owner.
        tail=min(owned_texts(a,F,S))
        if len(a)!=len(b) or len(a)!=len(c):
            raise ValueError('STAGE shared-tail capacity changed')
        adjusted=bytearray(b)
        adjusted[tail:]=a[tail:]
        text_mask=safe_text(a,F,S)
        for p in range(0,len(a)-3,4):
            x=u32(a,p)
            if not any(text_mask[p:p+4]) and BASE<=x<BASE+len(a):
                if p<tail and x>=BASE+tail and u32(b,p)-x not in (0x800,0x7F0,0x7E0,0x6B0):
                    raise ValueError('STAGE shared-tail owner drift at %#x'%p)
                if p>=tail or x>=BASE+tail:
                    struct.pack_into('<I',adjusted,p,x+0x800)
        b=bytes(adjusted)
    out=bytearray(b)
    required=len(c)+shift(len(c))
    if required>len(out):out.extend(bytes(required-len(out)))
    mask=safe_text(a,F,S)
    # Byte-edit ownership is separate from pointer ownership. New English text
    # allocated after the Japanese decoded length is preserved but reported.
    conflicts=[]
    for off in range(0,len(c),4):
        z=c[off:off+4];x=a[off:off+4]
        if x==z:continue
        target=off+shift(off)
        y=b[target:target+len(z)]
        if len(z)==4 and len(x)==4:
            xv,zv=u32(x,0),u32(z,0)
            if off in (0x28,0x2C):
                # Container boundaries are structural; historical English
                # generic pointer passes mistook them for relocated text.
                continue
            if BASE<=xv<BASE+len(a) and BASE<=zv<BASE+len(c) and not any(mask[off:off+4]):
                if target+4>len(b) or not BEST<=u32(b,target)<BEST+len(b):
                    conflicts.append([hex(off),'native pointer owner mismatch']);continue
                struct.pack_into('<I',out,target,zv+0x800+shift(zv-BASE))
                continue
        if x and len(y)==len(x) and y!=x:
            for k in range(len(z)):
                if x[k]!=z[k] and x[k]!=y[k] and y[k]!=z[k] and off+k<len(mask) and not mask[off+k]:
                    conflicts.append([hex(off+k),'non-text three-way conflict',x[k],y[k],z[k]])
        out[target:target+len(z)]=z
    if conflicts:
        raise ValueError('STAGE %d: %s'%(index,json.dumps(conflicts[:16])))
    owners=0
    english_texts=translated_texts(a,c,F,S)
    original_texts=owned_texts(a,F,S)
    native_owners={p for ps in original_texts.values() for p in ps}
    pointers=[]
    corrections=[]
    for offset,locations in english_texts.items():
        text=F.text_at(c,offset)
        actual_owners=[p for p in locations if p in native_owners]
        if not actual_owners:continue
        if index==150 and 0x1300 in actual_owners:
            native_target=u32(native,0x1300)-BEST
            if b'$n' not in F.text_at(native,native_target):
                raise ValueError('Best protagonist-name correction preimage changed')
            revised=text.replace(b'Rand!',b'$n!').replace(b'Land!',b'$n!')
            if b'$n!' not in revised:raise ValueError('Best protagonist-name English binding needs review')
            text=revised;corrections.append('Use renamed protagonist in Jiron dialogue')
        dest=offset+shift(offset)
        out[dest:dest+len(text)+1]=text+b'\0'
        for owner in actual_owners:
            p=owner+shift(owner)
            if not BEST<=u32(b,p)<BEST+len(b):
                raise ValueError('STAGE %d owner %#x is not native text pointer'%(index,owner))
            struct.pack_into('<I',out,p,BEST+dest)
            pointers.append((p,text));owners+=1
    # Validate by dereferencing the output, not by counting writes.
    for p,text in pointers:
        t=u32(out,p)-BEST
        end=out.find(b'\0',t)
        if end<0 or bytes(out[t:end])!=text:
            raise ValueError('STAGE %d translated pointer changed at %#x'%(index,p))
    if len(out)!=len(native):raise ValueError('Scenario exceeded native decoded allocation')
    return bytes(out),dict(index=index,owners=owners,bytes=len(out),source_bytes=source_bytes,
                          official_layout_growth=len(native)-len(a),sha256=sha(out),corrections=corrections,
                          compacted_texts=compacted)


def run(root,tools_dir):
    sys.path.insert(0,str(tools_dir))
    import fix_stranded_strings as F
    import fix_struct_intrusions as S
    root=Path(root)
    records=[];errors=[]
    for i in range(205):
        try:
            abc=[(root/'decoded'/v/'DATA/STAGE.BIN'/('%03d.bin'%i)).read_bytes() for v in ['original','best','english']]
            data,proof=build_record(i,*abc,(F,S))
            p=root/'decoded/output/DATA/STAGE.BIN'/('%03d.bin'%i)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            records.append(proof)
        except ValueError as exc:
            errors.append(str(exc))
    dump(root/'stage-port.json',dict(records=records,errors=errors,owners=sum(r['owners'] for r in records)))
    print(json.dumps(dict(passed=len(records),errors=errors,owners=sum(r['owners'] for r in records)),indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
