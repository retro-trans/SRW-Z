"""Port this project's English runtime to the hash-locked native Best ELF."""
import bisect
import json
import struct
from pathlib import Path
from disc import dump, sha
from elfmap import BASE, START, CODE_END, u32, normal

CAVE = 0x78A070
CAVE_FILE = 0x34D770
NATIVE_END = 0x789D00
DELTA = 0x800


def signed16(value):
    value &= 65535
    return value - 65536 if value >= 32768 else value


def register_written(w, reg):
    op,rs,rt,rd=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31
    if op in (0,28):
        return rd == reg and (w&63) not in (8,12,13,16,17,18,19,24,25,26,27)
    if op in (1,2,4,5,6,7,20,21,22,23,40,41,42,43,44,45,46,47,57,61,63):
        return False
    if op == 3:
        return reg == 31
    return rt == reg


class ElfPort:
    def __init__(self, root, layout):
        self.root=Path(root)
        self.layout=layout
        self.a,self.b,self.c=[(self.root/'inputs'/v/'SLPS_258.87').read_bytes() for v in ['original','best','english']]
        data=json.loads((self.root/'elf_analysis/native-map.json').read_text())
        if data['original_sha256']!=sha(self.a) or data['best_sha256']!=sha(self.b):
            raise ValueError('Native instruction map belongs to different source discs')
        self.code={o:t+o-lo for lo,hi,t in data['blocks'] for o in range(lo,hi,4)}
        self.spans=layout['elf_spans']
        self.starts=[r[0] for r in self.spans]
        self.cave_header=self.cave_segment(self.c)
        self.cave_size=self.cave_header[4]
        self.cave_end=CAVE+self.cave_size
        self.out=bytearray(self.b)
        self.writes={}
        self.address_uses=[]

    @staticmethod
    def cave_segment(data):
        po=u32(data,0x1c);ps,pn=struct.unpack_from('<HH',data,0x2a)
        for i in range(pn):
            row=struct.unpack_from('<8I',data,po+i*ps)
            if row[0]==1 and row[2]==CAVE:return row
        raise ValueError('English source has no expected runtime segment')

    def map_file(self, off):
        aligned=off&~3
        if START<=off<CODE_END:
            if aligned not in self.code:raise ValueError('Unmapped code offset: '+hex(off))
            return self.code[aligned]+(off&3)
        i=bisect.bisect_right(self.starts,off)-1
        if i>=0 and off<self.spans[i][1]:
            return self.spans[i][2]+off-self.spans[i][0]
        # Immediately after Best's shortened support-attack explanation, both
        # editions resume at the same +0x800 offset (checked against native).
        if 0x3364A8<=off<0x3364B8:
            return off+0x7F8
        raise ValueError('Unmapped data offset: '+hex(off))

    def address(self, va):
        if CAVE<=va<=self.cave_end or va==0x78CD00:
            return va+DELTA
        if BASE+0x34D700<=va<=NATIVE_END:
            return va+DELTA
        if 0x100000<=va<BASE+0x34D700:
            return self.map_file(va-BASE)+BASE
        # Heap objects are discovered through native pointers; hardware
        # scratchpad/GS addresses and non-address constants remain unchanged.
        return va

    def put(self, off, payload, reason):
        end=off+len(payload)
        if end>len(self.out):self.out.extend(bytes(end-len(self.out)))
        self.out[off:end]=payload
        for p in range(off,end):self.writes[p]=reason

    def word(self, off, w, reason):
        self.put(off,struct.pack('<I',w&0xffffffff),reason)

    def source_word(self, pc):
        off=CAVE_FILE+pc-CAVE if CAVE<=pc<self.cave_end else pc-BASE
        return u32(self.c,off)

    def target_offset(self, pc):
        return CAVE_FILE+DELTA+pc-CAVE if CAVE<=pc<self.cave_end else self.map_file(pc-BASE)

    def find_hi(self, pc, word, code_set=None):
        rs=(word>>21)&31
        if not rs:return None
        for before in range(pc-4,max(pc-132,CAVE-4 if pc>=CAVE else 0xFFFFC),-4):
            if code_set is not None and before not in code_set:return None
            w=self.source_word(before)
            if w>>26==15 and (w>>16)&31==rs:return before,w&65535
            # Indexed loads can add a variable offset between the LUI and
            # address low half: lui t0,hi; addu t0,t0,index; lbu t0,lo(t0).
            # The additive index does not consume the relocatable constant.
            if w>>26==0 and w&63 in (0x21,0x2D) and (w>>11)&31==rs and rs in ((w>>21)&31,(w>>16)&31):
                continue
            if register_written(w,rs):return None
            if w>>26 in (2,3) or w>>26==0 and w&63 in (8,9):return None
        return None

    def port_instruction(self, pc, code_set=None):
        w=self.source_word(pc);op=w>>26
        target_pc=self.address(pc)
        result=w
        if op in (2,3):
            destination=(w&0x3ffffff)<<2
            result=(w&0xfc000000)|(self.address(destination)>>2)
        elif op in (1,4,5,6,7,20,21,22,23):
            destination=pc+4+signed16(w)*4
            distance=(self.address(destination)-target_pc-4)//4
            if not -32768<=distance<=32767:raise ValueError('Branch displacement overflow')
            result=(w&0xffff0000)|(distance&65535)
        elif op in (9,13,25,32,33,35,36,37,39,40,41,43,49,55,57,63):
            hi=self.find_hi(pc,w,code_set)
            if hi:
                hipc,upper=hi
                value=(upper<<16)+((w&65535) if op==13 else signed16(w))
                if pc<CAVE:
                    nativehi=u32(self.a,hipc-BASE)&65535
                    nativelo=u32(self.a,pc-BASE)
                    nativevalue=(nativehi<<16)+((nativelo&65535) if op==13 else signed16(nativelo))
                    # Some engine UI words are assembled as literal text using
                    # lui/ori. "Air" and "ize" resemble RAM addresses after
                    # translation, but their Japanese preimages are text.
                    if not 0x100000<=nativevalue<=NATIVE_END:
                        self.word(self.target_offset(pc),result,'English literal instruction')
                        return
                mapped=self.address(value)
                if value!=mapped:
                    newhi=(mapped>>16) if op==13 else ((mapped+0x8000)>>16)
                    hiword=self.source_word(hipc)
                    self.word(self.target_offset(hipc),(hiword&0xffff0000)|(newhi&65535),'address high half')
                    result=(w&0xffff0000)|(mapped&65535)
                    self.address_uses.append(dict(pc=hex(pc),source=hex(value),target=hex(mapped)))
        self.word(self.target_offset(pc),result,'English instruction')

    def cave_code(self):
        pending=[CAVE]
        for off in range(START,CODE_END,4):
            w=u32(self.c,off)
            if w>>26 in (2,3) and CAVE<=((w&0x3ffffff)<<2)<self.cave_end:
                pending.append((w&0x3ffffff)<<2)
        visited=set()
        while pending:
            pc=pending.pop()
            if pc in visited or not CAVE<=pc<self.cave_end:continue
            if pc&3:raise ValueError('Misaligned runtime entry')
            visited.add(pc)
            w=self.source_word(pc);op=w>>26
            if op in (2,3):
                pending.append((w&0x3ffffff)<<2)
                visited.add(pc+4)
                if op==3:pending.append(pc+8)
            elif op in (1,4,5,6,7,20,21,22,23):
                pending.extend([pc+8,pc+4+signed16(w)*4]);visited.add(pc+4)
            elif op==0 and w&63 in (8,9):
                visited.add(pc+4)
                if w&63==9:pending.append(pc+8)
            else:pending.append(pc+4)
        return visited

    def build(self):
        # Preserve Best's native load segments, reserving the same extra three
        # pages above Best's _end as our Original runtime reserves above its own.
        native_ph=u32(self.b,0x1c);size,count=struct.unpack_from('<HH',self.b,0x2a)
        end=max(u32(self.b,native_ph+i*size+8)+u32(self.b,native_ph+i*size+20) for i in range(count))
        if end!=NATIVE_END+DELTA:raise ValueError('Unexpected Best memory ceiling')
        if native_ph+(count+1)*size>START:raise ValueError('No room for English program header')
        payload=self.c[CAVE_FILE:CAVE_FILE+self.cave_size]
        if len(payload)!=self.cave_size:raise ValueError('Truncated English runtime')
        self.put(CAVE_FILE+DELTA,payload,'English runtime segment')
        last=self.b[native_ph+(count-1)*size:native_ph+count*size]
        self.put(native_ph+count*size,last,'preserve final native BSS header')
        row=list(self.cave_header);row[1]+=DELTA;row[2]+=DELTA;row[3]+=DELTA
        self.put(native_ph+(count-1)*size,struct.pack('<8I',*row),'English program header')
        self.put(0x2c,struct.pack('<H',count+1),'program header count')
        self.word(0x20,0,'strip obsolete section table')
        self.put(0x30,b'\0'*4,'strip obsolete section count')
        changed_code=[]
        for off in range(START,CODE_END,4):
            x,z=u32(self.a,off),u32(self.c,off)
            if x==z:continue
            target=self.map_file(off);y=u32(self.b,target)
            if normal(x)!=normal(y):raise ValueError('Official code conflict at '+hex(off+BASE))
            self.port_instruction(off+BASE)
            changed_code.append([hex(off+BASE),hex(target+BASE),hex(x),hex(y),hex(u32(self.out,target))])
        # Native archive tables will be replaced after component compression.
        excluded={o for r in self.layout['archive_tables'] for o in range(r['original_start'],r['original_start']+4*r['count'],4)}
        slot=self.layout['elf_support_attack_slot']
        data_conflicts=[]
        for off in range(CODE_END,0x34D700,4):
            if off in excluded or slot['original_start']<=off<slot['original_end']:continue
            x,z=u32(self.a,off),u32(self.c,off)
            if x==z:continue
            target=self.map_file(off);y=u32(self.b,target)
            if x!=y:
                # A native address field must retain its edition relocation.
                if 0x100000<=x<=NATIVE_END and self.address(x)==y and 0x100000<=z<=0x78CD00:
                    z=self.address(z)
                else:
                    # Translated fixed strings may differ between editions;
                    # preserve exact per-byte preimages outside changed bytes.
                    if any(self.a[off+k]!=self.b[target+k] and self.c[off+k]==self.a[off+k] for k in range(4)):
                        mixed=bytearray(struct.pack('<I',z))
                        for k in range(4):
                            if self.c[off+k]==self.a[off+k]:mixed[k]=self.b[target+k]
                        z=u32(mixed,0)
                    data_conflicts.append(hex(off+BASE))
            elif 0x100000<=x<=NATIVE_END and 0x100000<=z<=0x78CD00 and x%4==0:
                # Only established native pointer fields are relocated, never
                # arbitrary English bytes that happen to resemble an address.
                try:
                    if self.address(x)==y:z=self.address(z)
                except ValueError:pass
            self.word(target,z,'English data field')
        text=b'Support attacks always score critical hits\x81D\0'
        capacity=slot['best_end']-slot['best_start']
        if len(text)>capacity:raise ValueError('Best support description overflow')
        self.put(slot['best_start'],text+bytes(capacity-len(text)),'Best corrected support description')
        code=self.cave_code()
        for pc in sorted(code):self.port_instruction(pc,code)
        # The two heap bases must agree and preserve Best's page offset.
        init=u32(self.out,0x1001d8-BASE)
        if init!=0x2484D500:raise ValueError('Best heap reservation did not relocate correctly: '+hex(init))
        break_at=self.map_file(0x3F3FB4-BASE)
        if u32(self.out,break_at)!=0x78D500:raise ValueError('Best libkernel break pointer mismatch')
        if CAVE+DELTA+self.cave_size>0x78D500:raise ValueError('English runtime overlaps heap')
        self.audit=dict(main_instructions=changed_code,cave_instruction_count=len(code),address_relocations=self.address_uses,
                        data_native_overlap=data_conflicts,heap_base=hex(0x78D500),cave_start=hex(CAVE+DELTA),cave_bytes=self.cave_size)
        return self.out

    def save(self):
        target=self.root/'components/SLPS_732.70'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(self.out)
        # No unaccounted changes to any byte from the native ELF.
        unexpected=[i for i,(a,b) in enumerate(zip(self.b,self.out)) if a!=b and i not in self.writes]
        if unexpected:raise ValueError('Undeclared ELF write')
        self.audit.update(sha256=sha(self.out),bytes=len(self.out),undeclared_writes=len(unexpected))
        dump(self.root/'elf-port.json',self.audit)


if __name__=='__main__':
    import sys
    layout=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    port=ElfPort(sys.argv[1],layout)
    port.build();port.save()
    print(json.dumps({k:port.audit[k] for k in ['cave_instruction_count','heap_base','cave_start','cave_bytes','sha256','undeclared_writes']},indent=2))
