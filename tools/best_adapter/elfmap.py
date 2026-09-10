"""Derive and audit native Original/Best instruction correspondence.

Matching is an analysis step, never permission to write unknown instructions.
The generated map records both native preimages for every mapped site.
"""
import difflib
import bisect
import json
import struct
from pathlib import Path
from disc import Disc, dump, sha

BASE = 0xFE580
START = 0x1A80
CODE_END = 0x2F2000


def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def normal(word):
    op = word >> 26
    if op in (2, 3):
        return word & 0xFC000000
    if op in (1, 4, 5, 6, 7, 20, 21, 22, 23):
        return word & 0xFFFF0000
    # Absolute data addresses are normally loaded with lui then a signed low
    # half. Other immediates remain part of the matching signature.
    if op in (9, 13, 15, 25) or ((word >> 21) & 31) in (1, 28) and op in (24, 32, 33, 35, 36, 37, 39, 40, 41, 43, 49, 55, 57, 63):
        return word & 0xFFFF0000
    return word


def analyze(original, best, english, directory, raw=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    a = Path(original).read_bytes() if raw else Disc(original).read('SLPS_258.87')
    b = Path(best).read_bytes() if raw else Disc(best).read('SLPS_732.70')
    c = Path(english).read_bytes() if raw else Disc(english).read('SLPS_258.87')
    for name, data in [('original', a), ('best', b), ('english', c)]:
        (directory / (name + '.elf')).write_bytes(data)
    aa = [normal(u32(a, off)) for off in range(START, CODE_END, 4)]
    bb = [normal(u32(b, off)) for off in range(START, CODE_END + 0x800, 4)]
    # Whole-image SequenceMatcher can become quadratic on repeated compiler
    # output. Unique 16-instruction anchors bound every detailed comparison.
    lookup = {}
    for j in range(len(bb)-15):
        key = tuple(bb[j:j+16])
        lookup[key] = j if key not in lookup else None
    candidates = []
    for i in range(0,len(aa)-15,8):
        j=lookup.get(tuple(aa[i:i+16]))
        if j is not None:
            candidates.append((i,j))
    tails, chain, previous = [], [], []
    for index,(i,j) in enumerate(candidates):
        k=bisect.bisect_left(tails,j)
        previous.append(chain[k-1] if k else -1)
        if k == len(tails): tails.append(j);chain.append(index)
        else: tails[k]=j;chain[k]=index
    selected=[]
    index=chain[-1]
    while index>=0:
        selected.append(candidates[index]);index=previous[index]
    selected.reverse()
    matches=[]
    for i,j in selected:
        if matches and i <= matches[-1][0]+matches[-1][2] and j-i == matches[-1][1]-matches[-1][0]:
            pi,pj,pn=matches[-1];matches[-1]=(pi,pj,max(pn,i+16-pi))
        elif not matches or i>=matches[-1][0]+matches[-1][2] and j>=matches[-1][1]+matches[-1][2]:
            matches.append((i,j,16))
    detailed=[]
    pi=pj=0
    for i,j,n in matches+[(len(aa),len(bb),0)]:
        if i>pi and j>pj and max(i-pi,j-pj)<8192:
            detailed.extend((pi+x,pj+y,k) for x,y,k in difflib.SequenceMatcher(None,aa[pi:i],bb[pj:j],autojunk=False).get_matching_blocks() if k>=4)
        detailed.append((i,j,n));pi=i+n;pj=j+n
    blocks = [(START+i*4,START+(i+n)*4,START+j*4) for i,j,n in sorted(detailed) if n>=4]
    mapped = {off: target+off-lo for lo,hi,target in blocks for off in range(lo,hi,4)}
    changed = []
    for off in range(START, CODE_END, 4):
        x, z = u32(a, off), u32(c, off)
        if x != z:
            t = mapped.get(off)
            changed.append(dict(original_va=hex(off+BASE), english=hex(z), original=hex(x), best_va=hex(t+BASE) if t is not None else None, best=hex(u32(b,t)) if t is not None else None))
    def headers(d):
        po = u32(d, 0x1C)
        ps, pn = struct.unpack_from('<HH',d,0x2A)
        return [list(struct.unpack_from('<8I',d,po+i*ps)) for i in range(pn)]
    report = dict(original_sha256=sha(a),best_sha256=sha(b),english_sha256=sha(c),
                  blocks=blocks, mapped_words=len(mapped), changed_code=changed,
                  unmapped_changes=[r for r in changed if r['best_va'] is None],
                  headers={v:headers(d) for v,d in [('original',a),('best',b),('english',c)]})
    dump(directory/'native-map.json',report)
    print(json.dumps(dict(mapped_words=len(mapped),changed_code_count=len(changed),unmapped_changes=report['unmapped_changes']),indent=2),flush=True)


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser()
    for k in ['original','best','english','out']:
        p.add_argument('--'+k,required=True)
    x=p.parse_args()
    analyze(x.original,x.best,x.english,x.out)
