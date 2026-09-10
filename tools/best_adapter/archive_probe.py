import json
import struct
import sys
from pathlib import Path
from disc import dump


def run(root, tools_dir, layout_path):
    sys.path.insert(0, str(tools_dir))
    import banlz
    root=Path(root)
    layout=json.loads(Path(layout_path).read_text(encoding='utf-8'))
    report={}
    for name in ['DATA/STAGE.BIN','DATA/COMPDATA.BN','DATA/HSFC.BIN','DATA/NISVDATA.BIN','DATA/MTVZKNPT.BIN']:
        values={}
        for version in ['original','best','english']:
            data=(root/'inputs'/version/name).read_bytes()
            if name=='DATA/STAGE.BIN':
                # The English build keeps native compressed record extents.
                hb=(root/'inputs'/version/'HEDBDY/HB.BIN').read_bytes()
                offsets=list(struct.unpack_from('<206I',hb,30320))
            elif name=='DATA/COMPDATA.BN':
                offsets=[0,len(data)]
            else:
                table=next(t for t in layout['archive_tables'] if t['member']==name)
                elf=(root/'inputs'/version/'SLPS_258.87').read_bytes()
                start=table['best_start' if version=='best' else 'original_start']
                offsets=list(struct.unpack_from('<%dI'%table['count'],elf,start))
                if offsets[-1]<len(data):offsets.append(len(data))
            chunks=[]
            for i,(lo,hi) in enumerate(zip(offsets,offsets[1:])):
                decoded,end=banlz.decompress_record(data[lo:hi])
                if decoded is None:
                    raise ValueError('%s %s chunk %d empty'%(version,name,i))
                out=root/'decoded'/version/name/('%03d.bin'%i)
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(decoded)
                chunks.append(dict(size=len(decoded),start=lo,end=hi))
            values[version]=chunks
        report[name]=values
        print(name,'counts', {v:len(z) for v,z in values.items()},flush=True)
        if name=='DATA/STAGE.BIN':
            print('stage length changes',[(i,a['size'],values['best'][i]['size'],values['english'][i]['size']) for i,a in enumerate(values['original']) if a['size'] != values['best'][i]['size'] or a['size']!=values['english'][i]['size']],flush=True)
    dump(root/'archive-analysis.json',report)


if __name__=='__main__':
    run(sys.argv[1],sys.argv[2],sys.argv[3])
