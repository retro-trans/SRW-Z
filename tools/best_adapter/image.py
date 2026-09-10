"""Assemble a separate Best candidate and verify every changed byte range."""
import json
import shutil
import struct
from pathlib import Path
from disc import Disc,SECTOR,dump,sha,file_sha


def sectors(n):return (n+SECTOR-1)//SECTOR


def plan(root):
    root=Path(root);manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    source=Disc(manifest['sources']['best'])
    dummy=source.entries['DMY/DMY.BIN'];cursor=dummy['lba']+8192
    limit=(dummy['lba']*SECTOR+dummy['size'])//SECTOR
    rows=[]
    for p in sorted((root/'components').rglob('*')):
        if not p.is_file():continue
        name=p.relative_to(root/'components').as_posix()
        if name=='VMAP.DAT':continue
        if name not in source.entries:raise ValueError('Unknown output member: '+name)
        old=source.entries[name];size=p.stat().st_size;lba=old['lba']
        if sectors(size)>sectors(old['size']):
            lba=cursor;cursor+=sectors(size)
            if cursor>limit:raise ValueError('Insufficient dummy allocation')
            with source.path.open('rb') as f:
                f.seek(lba*SECTOR)
                if any(f.read(sectors(size)*SECTOR)):raise ValueError('Relocation would overwrite nonzero dummy bytes')
        rows.append(dict(member=name,path=str(p.resolve()),lba=lba,size=size,sha256=file_sha(p),
                         native_lba=old['lba'],native_size=old['size'],directory_record=old['directory_record']))
    # Components must never overlap each other or other live files.
    names={r['member'] for r in rows}
    extents=[(r['lba'],r['lba']+sectors(r['size']),r['member']) for r in rows]
    extents += [(v['lba'],v['lba']+sectors(v['size']),n) for n,v in source.entries.items() if n not in names and n!='DMY/DMY.BIN']
    extents.sort()
    for (a,b,n),(c,d,m) in zip(extents,extents[1:]):
        if b>c:raise ValueError('ISO members overlap: %s / %s'%(n,m))
    vmap=bytearray(source.read('VMAP.DAT'))
    for r in rows:
        if r['member'] in source.runtime:
            at=source.runtime[r['member']]['vmap_offset']+40
            struct.pack_into('<II',vmap,at,r['lba'],sectors(r['size']))
    dump(root/'iso-plan.json',dict(source=str(source.path),source_sha256='950e2759d0d7482387d97d6df31325d9e352097a23e0bb4724073d1538d8cf77',members=rows))
    return source,rows,bytes(vmap)


def assemble(root,output):
    root=Path(root);output=Path(output).resolve()
    source,rows,vmap=plan(root)
    inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if output in [Path(p).resolve() for p in inputs['sources'].values()]:raise ValueError('Output must be separate from every input')
    if output.exists():raise ValueError('Output already exists; choose a new candidate filename')
    if file_sha(source.path)!='950e2759d0d7482387d97d6df31325d9e352097a23e0bb4724073d1538d8cf77':raise ValueError('Native Best ISO changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=output.with_name(output.name+'.partial')
    if staging.exists():raise ValueError('Partial output already exists; inspect it before retrying')
    print('Copying verified native Best ISO',flush=True)
    shutil.copyfile(str(source.path),str(staging))
    allowed=[]
    with staging.open('r+b') as f:
        for r in rows:
            payload=Path(r['path']).read_bytes()
            if sha(payload)!=r['sha256']:raise ValueError('Component changed during assembly')
            f.seek(r['lba']*SECTOR);f.write(payload)
            allowed.append((r['lba']*SECTOR,r['lba']*SECTOR+len(payload)))
            pos=r['directory_record']+2;f.seek(pos)
            f.write(struct.pack('<I',r['lba'])+struct.pack('>I',r['lba']));allowed.append((pos,pos+8))
            pos=r['directory_record']+10;f.seek(pos)
            f.write(struct.pack('<I',r['size'])+struct.pack('>I',r['size']));allowed.append((pos,pos+8))
        pos=source.entries['VMAP.DAT']['lba']*SECTOR
        f.seek(pos);f.write(vmap);allowed.append((pos,pos+len(vmap)))
    print('Verifying ISO directory, runtime file table and untouched ranges',flush=True)
    image=Disc(staging);runtime=Disc(staging,runtime=True)
    for r in rows:
        if image.read(r['member'])!=Path(r['path']).read_bytes():raise ValueError('ISO member readback failed')
        if image.entries[r['member']]['lba']!=r['lba']:raise ValueError('ISO LBA readback failed')
        if r['member'] in runtime.runtime:
            vm=runtime.runtime[r['member']]
            if vm['lba']!=r['lba'] or vm['sectors']!=sectors(r['size']):raise ValueError('Runtime VMAP differs from ISO directory')
    if image.read('SYSTEM.CNF')!=source.read('SYSTEM.CNF'):raise ValueError('Native boot configuration changed')
    # Stream all untouched gaps. This includes every original code/resource byte
    # outside the explicit component replacements and directory/table fields.
    ranges=[]
    for lo,hi in sorted(allowed):
        if ranges and lo<=ranges[-1][1]:ranges[-1]=(ranges[-1][0],max(hi,ranges[-1][1]))
        else:ranges.append((lo,hi))
    cursor=0
    with source.path.open('rb') as a,staging.open('rb') as b:
        for lo,hi in ranges+[(source.size,source.size)]:
            a.seek(cursor);b.seek(cursor);left=lo-cursor
            while left:
                n=min(left,8<<20)
                if a.read(n)!=b.read(n):raise ValueError('Unexpected change outside replacement ranges')
                left-=n
            cursor=hi
    if staging.stat().st_size!=source.size:raise ValueError('ISO size changed')
    digest=file_sha(staging)
    staging.rename(output)
    dump(root/'iso-verification.json',dict(output=str(output),sha256=digest,bytes=output.stat().st_size,
          changed_members=len(rows),relocated_members=[r['member'] for r in rows if r['lba']!=r['native_lba']],
          untouched_ranges_verified=True,runtime_and_iso_tables_agree=True,hardware_tested=False))
    print('Candidate ISO verified:',output,flush=True)
    return output


if __name__=='__main__':
    import sys
    assemble(sys.argv[1],sys.argv[2])
