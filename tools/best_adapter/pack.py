"""Compress translated records, update Best tables, and copy identical-layout assets."""
import concurrent.futures
import json
import struct
import sys
from pathlib import Path
from disc import dump,sha


def compress_job(job):
    root,tools_dir,name,index=job
    sys.path.insert(0,tools_dir)
    import banlz,banlz_strict
    root=Path(root)
    data=(root/'decoded/output'/name/('%03d.bin'%index)).read_bytes()
    digest=sha(data)
    cache=root/'compressed'/name/('%03d-%s.bin'%(index,digest[:16]))
    if cache.exists():blob=cache.read_bytes()
    else:
        analysis=json.loads((root/'archive-analysis.json').read_text(encoding='utf-8'))[name]
        blob=None
        for v in ('best','english','original'):
            old=(root/'decoded'/v/name/('%03d.bin'%index)).read_bytes()
            if old==data:
                row=analysis[v][index]
                archive=(root/'inputs'/v/name).read_bytes()
                stream=archive[row['start']:row['end']]
                decoded,end=banlz.decompress_record(stream)
                if decoded!=data:raise ValueError('Source record cache mismatch')
                blob=stream[:end];break
        if blob is None:blob=banlz.compress_record(data)
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(blob)
    decoded,end=banlz.decompress_record(blob)
    if decoded!=data or end!=len(blob):raise ValueError('Compressed record readback mismatch')
    total,flags,start=banlz.parse_header(blob)
    strict,issues=banlz_strict.verify(blob,start,total)
    if issues or strict!=data:raise ValueError('Game-strict decompression failed: '+str(issues))
    return name,index,blob,digest


def run(root,tools_dir,layout,workers=6):
    root=Path(root);manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    analysis=json.loads((root/'archive-analysis.json').read_text(encoding='utf-8'))
    jobs=[(str(root.resolve()),str(Path(tools_dir).resolve()),name,i) for name,versions in analysis.items()
          for i in range(len(versions['best']))]
    packed={};hashes={}
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for done,result in enumerate(pool.map(compress_job,jobs),1):
            name,index,blob,digest=result
            packed.setdefault(name,{})[index]=blob;hashes.setdefault(name,{})[index]=digest
            if done%50==0:print('Compressed and verified %d/%d records'%(done,len(jobs)),flush=True)
    elf_path=root/'components/SLPS_732.70';elf=bytearray(elf_path.read_bytes());report=[]
    hb=bytearray((root/'inputs/best/HEDBDY/HB.BIN').read_bytes())
    for name,chunks in packed.items():
        data=bytearray();offsets=[0]
        for i in range(len(chunks)):
            data.extend(chunks[i]);data.extend(bytes((-len(data))%16));offsets.append(len(data))
        if name=='DATA/STAGE.BIN':
            capacity=(manifest['members']['best'][name]['size']+2047)//2048*2048
            if len(data)>capacity:
                dump(root/'stage-compression-overflow.json',dict(bytes=len(data),capacity=capacity,excess=len(data)-capacity))
                raise ValueError('STAGE compression exceeds native allocation by %d bytes'%(len(data)-capacity))
            struct.pack_into('<206I',hb,30320,*offsets)
        elif name!='DATA/COMPDATA.BN':
            table=next(t for t in layout['archive_tables'] if t['member']==name)
            values=offsets[:table['count']]
            if len(values)!=table['count']:raise ValueError('Archive table count drift')
            struct.pack_into('<%dI'%len(values),elf,table['best_start'],*values)
        p=root/'components'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        report.append(dict(member=name,bytes=len(data),sha256=sha(data),offsets=offsets,decoded_hashes=hashes[name]))
        print(name,'packed',len(data),flush=True)
    # All other changed assets have identical native bytes across the editions.
    copied=[]
    for row in manifest['changed']:
        name=row['member']
        if name in packed or name in ('VMAP.DAT','BTL/SRVC.BIN','BTL/SRVC.SEG','SLPS_258.87'):continue
        a=manifest['members']['original'][name]['sha256'];b=manifest['members']['best'][name]['sha256']
        if a!=b:raise ValueError('Unhandled Best resource: '+name)
        data=(root/'inputs/english'/name).read_bytes()
        p=root/'components'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        copied.append(dict(member=name,bytes=len(data),sha256=sha(data)))
        for table in layout['archive_tables']:
            if table['member']==name:
                source=(root/'inputs/english/SLPS_258.87').read_bytes();n=table['count']*4
                elf[table['best_start']:table['best_start']+n]=source[table['original_start']:table['original_start']+n]
    p=root/'components/HEDBDY/HB.BIN';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(hb)
    elf_path.write_bytes(elf)
    dump(root/'archive-port.json',dict(archives=report,copied=copied,elf_sha256=sha(elf),hb_sha256=sha(hb)))


if __name__=='__main__':run(sys.argv[1],sys.argv[2],json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')))
