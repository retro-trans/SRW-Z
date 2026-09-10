"""Read output through actual pointers and archive tables before ISO assembly."""
import json
import struct
import sys
from pathlib import Path
from disc import dump,sha
from elf import ElfPort,CAVE,CAVE_FILE,DELTA,BASE
import stage
from subtitles import load,native_layout,at,words


def run(root,tools_dir,layout):
    root=Path(root);sys.path.insert(0,str(tools_dir))
    import banlz,banlz_strict,fix_stranded_strings as F,fix_struct_intrusions as S
    plan=json.loads((root/'archive-port.json').read_text(encoding='utf-8'))
    elf=(root/'components/SLPS_732.70').read_bytes()
    hb=(root/'components/HEDBDY/HB.BIN').read_bytes()
    decoded={};count=0
    for archive in plan['archives']:
        name=archive['member'];blob=(root/'components'/name).read_bytes()
        offsets=archive['offsets']
        if sha(blob)!=archive['sha256']:raise ValueError('Packed component changed')
        if name=='DATA/STAGE.BIN':actual=list(struct.unpack_from('<206I',hb,30320))
        elif name=='DATA/COMPDATA.BN':actual=offsets
        else:
            table=next(t for t in layout['archive_tables'] if t['member']==name)
            actual=list(struct.unpack_from('<%dI'%table['count'],elf,table['best_start']))
        if actual!=offsets[:len(actual)] or len(actual)<len(offsets)-1:raise ValueError('Runtime archive table mismatch')
        for i,(lo,hi) in enumerate(zip(offsets,offsets[1:])):
            if lo%16 or hi>len(blob):raise ValueError('Archive extent alignment/bounds failure')
            data,end=banlz.decompress_record(blob[lo:hi]);total,flags,start=banlz.parse_header(blob[lo:hi])
            strict,issues=banlz_strict.verify(blob[lo:hi],start,total)
            if issues or strict!=data:raise ValueError('Game decoder safety failure')
            if sha(data)!=archive['decoded_hashes'][str(i)]:raise ValueError('Decoded payload mismatch')
            decoded[name,i]=data;count+=1
    text_count=0
    for i in range(205):
        a,c,b=[(root/'decoded'/v/'DATA/STAGE.BIN'/('%03d.bin'%i)).read_bytes() for v in ('original','english','best')]
        out=decoded['DATA/STAGE.BIN',i]
        if len(out)!=len(b):raise ValueError('Scenario decoded allocation changed')
        if a==c:
            if out!=b:raise ValueError('Untranslated scenario lost Best native changes')
            continue
        for t,owners in stage.translated_texts(a,c,F,S).items():
            expected=F.text_at(c,t)
            for p in owners:
                # Record 161's six audited name owners stay at native offsets;
                # only their target text pool moves by 0x80.
                q=p+(128 if i==26 else 0)
                target=stage.u32(out,q)-stage.BEST
                wanted=expected.replace(b'Rand!',b'$n!').replace(b'Land!',b'$n!') if i==150 and p==0x1300 else expected
                if not 0<=target<len(out) or F.text_at(out,target)!=wanted:
                    raise ValueError('Scenario %d source text changed at owner %#x'%(i,p))
                text_count+=1
    native=load(root,'best');data=(root/'components/BTL/SRVC.BIN').read_bytes()
    seg=(root/'components/BTL/SRVC.SEG').read_bytes();offsets=words(seg)
    if seg!=(root/'inputs/best/BTL/SRVC.SEG').read_bytes():raise ValueError('Best native subtitle extents changed')
    if offsets[-1]!=len(data) or any(o%16 for o in offsets):raise ValueError('PS2 subtitle alignment failure')
    subtitle_count=0
    for i,(lo,hi) in enumerate(zip(offsets,offsets[1:])):
        p,records,end=native_layout(native[i]);out=data[lo:hi]
        if p is None:
            if out!=native[i]:raise ValueError('Opaque subtitle block changed')
            continue
        if out[:p]!=native[i][:p] or out[end:]!=native[i][end:]:raise ValueError('Native subtitle metadata/tail changed')
        actual=at(out,p,len(records))
        if [r[0] for r in actual]!=[r[0] for r in records]:raise ValueError('Best voice IDs changed')
        subtitle_count+=len(actual)
    port=ElfPort(root,layout);port.build()
    # Archive offsets are the only post-link modifications to the runtime ELF.
    expected=bytearray(port.out)
    for table in layout['archive_tables']:
        n=4*table['count'];p=table['best_start'];expected[p:p+n]=elf[p:p+n]
    if bytes(expected)!=elf:raise ValueError('ELF differs outside compiled archive tables')
    # Regression guards for indexed LUI+ADDU+LBU references found during porting.
    for old,target in ((0x78B940,0xC160),(0x78C268,0xD0A0),(0x78C2C8,0xC160)):
        if stage.u32(elf,CAVE_FILE+DELTA+old-CAVE)&65535!=target:raise ValueError('Indexed font-table address not relocated')
    if subtitle_count!=58751:raise ValueError('Best subtitle coverage changed')
    report=dict(archive_records=count,stage_records=205,stage_text_references=text_count,subtitle_records=subtitle_count,
                srvc_alignment=16,native_stage_allocations_preserved=True,strict_game_decoder=True,
                best_voice_metadata_and_tails_preserved=True,elf_archive_tables_verified=True,
                copied_assets=len(plan['copied']),hardware_tested=False)
    dump(root/'verification.json',report);print(json.dumps(report,indent=2),flush=True)
    return report


if __name__=='__main__':run(sys.argv[1],sys.argv[2],json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')))
