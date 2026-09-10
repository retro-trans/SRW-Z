"""Port indexed captions while retaining Best voice metadata and opaque tails."""
import collections
import difflib
import json
import struct
import sys
from pathlib import Path
from disc import dump,sha


def words(b):return struct.unpack('<%dI'%(len(b)//4),b)
def word(b,p):return struct.unpack_from('<I',b,p)[0]


def at(raw,index,count):
    pool=index+count*8
    records=[]
    for n in range(count):
        meta,off=struct.unpack_from('<II',raw,index+8*n)
        start=pool+off
        if start>=len(raw) or (off and raw[start-1]):raise ValueError('Invalid caption offset')
        end=raw.find(b'\0',start)
        if end<0:raise ValueError('Unterminated caption')
        records.append((meta,raw[start:end+1]))
    return records


def native_layout(raw):
    if len(raw)<8 or raw[:2]!=b'\0O':raise ValueError('Invalid SRVC block header')
    count=struct.unpack_from('<H',raw,6)[0]
    if not count:return None,[],8
    matches=[]
    for p in range(8,len(raw)-8*count,4):
        if word(raw,p+4):continue
        pool=p+8*count
        cursor=0
        good=True
        for n in range(count):
            offset=word(raw,p+8*n+4)
            if offset!=cursor:good=False;break
            end=raw.find(b'\0',pool+cursor)
            if end<0:good=False;break
            # Native indexed text uses printable Shift-JIS and literal \\n.
            try:txt=raw[pool+cursor:end].decode('cp932')
            except UnicodeDecodeError:good=False;break
            if not txt or any(ord(c)<32 for c in txt):good=False;break
            cursor=end-pool+1
        if good:matches.append((p,at(raw,p,count),pool+cursor))
    if len(matches)!=1:raise ValueError('%d native caption index candidates'%len(matches))
    return matches[0]


def load(root,version):
    r=root/'inputs'/version/'BTL'
    data=(r/'SRVC.BIN').read_bytes()
    offsets=words((r/'SRVC.SEG').read_bytes())
    if offsets[0]!=0 or offsets[-1]>len(data):raise ValueError('Invalid SEG endpoints')
    return [data[a:b] for a,b in zip(offsets,offsets[1:])]


def run(root,contract):
    root=Path(root)
    aa,bb,cc=[load(root,v) for v in ('original','best','english')]
    originals=[];bests=[];english=[];input_repairs=[];prefix_diffs=[];metadata_diffs=[]
    binding=collections.defaultdict(set)
    for i,(a,b,c) in enumerate(zip(aa,bb,cc)):
        try:
            ap,ar,ae=native_layout(a);bp,br,be=native_layout(b)
            try:cr=[] if ap is None else at(c,ap,len(ar))
            except ValueError:
                # Historical English imports kept the string order but left
                # stale Japanese index offsets in several blocks. Recover only
                # complete, quoted captions at the native header-derived pool.
                cursor=ap+8*len(ar);cr=[]
                for n in range(len(ar)):
                    end=c.find(b'\0',cursor)
                    if end<0 or c[cursor:cursor+1]!=b'"' or c[end-1:end]!=b'"':
                        raise ValueError('English indexed pool cannot be recovered by order')
                    cr.append((word(c,ap+n*8),c[cursor:end+1]));cursor=end+1
                input_repairs.append(i)
            if a[:8]!=c[:8]:raise ValueError('English header differs')
            allowed={ap+n*8+k for n in range(len(ar)) for k in range(4,8)} if ap is not None else set()
            end=ap+8*len(ar) if ap is not None else len(a)
            prefix_diffs.extend([dict(block=i,offset=p) for p,(x,y) in enumerate(zip(a[:ap],c[:ap])) if x!=y])
            for n,((am,jp),(cm,en)) in enumerate(zip(ar,cr)):
                if am!=cm:metadata_diffs.append(dict(block=i,record=n,original=am,english=cm))
                if not en or any(ch<32 for ch in en[:-1]):raise ValueError('Non-text English caption')
                binding[sha(jp)].add(en)
            originals.append((ap,ar,ae));bests.append((bp,br,be));english.append(cr)
        except ValueError as exc:raise ValueError('SRVC %d: %s'%(i,exc))
    # Match source text by fingerprints; the public adapter need not embed
    # Japanese dialogue, which is read from the user's own discs.
    aliases={r['best_sha256']:r['original_sha256'] for r in contract['battle_source_aliases']}
    result=bytearray();offsets=[0];proof=[];errors=[]
    for i,(a,b,c) in enumerate(zip(aa,bb,cc)):
        ap,ar,ae=originals[i];bp,br,be=bests[i];cr=english[i]
        if bp is None:
            out=b
        else:
            # Bind repeated Japanese lines by their position within the block.
            old=[sha(r[1]) for r in ar];new=[aliases.get(sha(r[1]),sha(r[1])) for r in br]
            local={}
            for block in difflib.SequenceMatcher(None,old,new,autojunk=False).get_matching_blocks():
                for k in range(block.size):local[block.b+k]=cr[block.a+k][1]
            texts=[]
            for n,jp in enumerate(new):
                if n in local:texts.append(local[n]);continue
                choices=binding.get(jp,set())
                if len(choices)!=1:
                    errors.append(dict(block=i,record=n,choices=len(choices),source_sha256=jp))
                    texts.append(br[n][1])
                else:texts.append(next(iter(choices)))
            pool=bp+8*len(br)
            out=bytearray(b[:pool]);cursor=0
            deduplicate=sum(map(len,texts))>be-pool
            seen={}
            for n,text in enumerate(texts):
                if deduplicate and text in seen:target=seen[text]
                else:
                    target=cursor;seen[text]=target
                    out.extend(text);cursor+=len(text)
                struct.pack_into('<I',out,bp+8*n+4,target)
            if cursor>be-pool:raise ValueError('SRVC %d native pool overflow'%i)
            out.extend(bytes(be-len(out)))
            # Opaque tail stays at its exact native address, including padding.
            out.extend(b[be:])
            out.extend(bytes((-len(out))%16))
            actual=at(out,bp,len(br))
            if actual!=[(r[0],t) for r,t in zip(br,texts)]:raise ValueError('Caption readback mismatch')
            if len(out)!=len(b) or out[be:]!=b[be:]:raise ValueError('Native SRVC tail moved')
            proof.append(dict(block=i,records=len(br),bytes=len(out),original_bytes=len(b),tail_bytes=len(b)-be,
                              headroom=be-pool-cursor,deduplicated=deduplicate))
        result.extend(out);result.extend(bytes((-len(result))%16));offsets.append(len(result))
    report=dict(records=sum(len(v[1]) for v in bests),original_records=sum(len(v[1]) for v in originals),
                errors=errors,blocks=proof,bytes=len(result),sha256=sha(result),alignment=16,
                input_stale_index_blocks=input_repairs,input_prefix_bytes_discarded=prefix_diffs,
                input_metadata_discarded=metadata_diffs)
    dump(root/'subtitle-port.json',report)
    print(json.dumps({k:report[k] for k in ('records','original_records','bytes','errors')},indent=2))
    if errors:raise ValueError('Unresolved Best subtitle bindings')
    if report['records']!=58751 or report['original_records']!=58740:raise ValueError('Unexpected indexed record coverage')
    out=root/'components/BTL';out.mkdir(parents=True,exist_ok=True)
    (out/'SRVC.BIN').write_bytes(result)
    (out/'SRVC.SEG').write_bytes(struct.pack('<%dI'%len(offsets),*offsets))


if __name__=='__main__':run(sys.argv[1],json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
