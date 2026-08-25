# -*- coding: utf-8 -*-
"""Does the link affect the characters before/after it? Anchor with zzz...zzz."""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_affect.bin")
ROWS = {7:(0x5710,66),8:(0x5760,58),9:(0x57a0,58),142:(0x84a0,31),144:(0x84e0,95),146:(0x8560,91)}
def fw(s): return ''.join(chr(ord(c)+0xFEE0) if 0x21<=ord(c)<=0x7E else ('\u3000' if c==' ' else c) for c in s)
LO,LC="\u300a","\u300b"
def lk(t): return LO+t+LC
TESTS = {
    # same zzz anchors, vary term length/width; compare gap zzz->term and term->zzz
    7:  ("Denzel", ["\u300czzz"+lk("X")+"zzz  1-char half\u300d"]),
    8:  ("Toby",   ["\u300czzz"+lk("Glory Star")+"zzz  10 half\u300d"]),
    9:  ("Denzel", ["\u300czzz Glory Star zzz  NO link\u300d"]),
    142:("Jerid",  ["\u300czzz"+lk(fw("X"))+"zzz  1 full\u300d"]),
    144:("Setsuko",["\u300czzz"+lk(fw("Glory Star"))+"zzz full\u300d"]),
    146:("Setsuko",["\u300cabcdefgh"+lk("Y")+"  vs below",
                    "\u3000abcdefgh  (same, no link)\u300d"]),
}
def build_string(r):
    spk,lines=TESTS[r]; return ("\n".join([spk]+lines)).encode("cp932")+b"\x00"
def replace_ptr(buf,oldp,newp):
    ob,nb,c,i=struct.pack("<I",oldp),struct.pack("<I",newp),0,0
    while True:
        j=buf.find(ob,i)
        if j<0: break
        if j%4==0: buf[j:j+4]=nb; c+=1; i=j+4
        else: i=j+1
    return c
def main():
    with open(BASE_ISO,"rb") as f: f.seek(STAGE_LBA*SECTOR); stage=bytearray(f.read(STAGE_SIZE))
    rec=bytearray(banlz.decompress_all(bytes(stage))[1][1])
    total,flags,at=banlz.parse_header(bytes(stage),SLOT_START); no={}
    for r in sorted(TESTS): no[r]=len(rec); rec+=build_string(r)
    for r in sorted(TESTS):
        off,nb=ROWS[r]; assert replace_ptr(rec,BASE+off,BASE+no[r])>=1
        for x in range(off,off+nb): rec[x]=0
    blob=banlz.compress_record(bytes(rec),flags); assert banlz.decompress_record(blob)[0]==bytes(rec)
    slot=SLOT_END-SLOT_START
    print("blob %d / slot %d -> %s"%(len(blob),slot,"FITS" if len(blob)<=slot else "TOO BIG")); assert len(blob)<=slot
    stage[SLOT_START:SLOT_END]=blob+b"\x00"*(slot-len(blob))
    assert banlz.decompress_all(bytes(stage))[1][1]==bytes(rec)
    import banlz_strict as bs; t2,fl2,at2=banlz.parse_header(bytes(stage),SLOT_START)
    print("strict:",len(bs.verify(bytes(stage),at2,t2)[1]))
    shutil.copyfile(BASE_ISO,OUT_ISO)
    with open(OUT_ISO,"r+b") as f: f.seek(STAGE_LBA*SECTOR); f.write(stage)
    print("wrote",OUT_ISO)
if __name__=="__main__": main()
