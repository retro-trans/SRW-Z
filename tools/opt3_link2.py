# -*- coding: utf-8 -*-
"""Link format 『《En》』 (JP structure, English inside) vs JP original.
The 』 immediately after 》 caps the underline; a space after 》 would let it run
to the next word. Width 33 in-game / 37 scene, 「」 quotes (-> blue names)."""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_link2.bin")
ROWS = {7:(0x5710,66),8:(0x5760,58),9:(0x57a0,58),142:(0x84a0,31),144:(0x84e0,95),146:(0x8560,91)}
GS = "\u300a\u30b0\u30ed\u30fc\u30ea\u30fc\u30fb\u30b9\u30bf\u30fc\u300b"   # 《グローリー・スター》
L = "\u300aGlory Star\u300b"                                              # 《Glory Star》
OB, CB = "\u300e", "\u300f"                                                # 『 』
TESTS = {
    7:  ("Denzel", ["\u300cJP original link below:\u300d",
                    "\u300c\u3053\u308c\u304c"+OB+GS+CB+"\u3060\u300d"]),
    8:  ("Toby",   ["\u300cWe are the "+OB+L+CB,
                    "\u3000team, tidy underline?\u300d"]),
    9:  ("Denzel", ["\u300cAssigned to "+OB+L+CB+" now,",
                    "\u3000does it look clean?\u300d"]),
    142:("Jerid",  ["\u300cJP original link below:\u300d",
                    "\u300c\u3053\u308c\u304c"+OB+GS+CB+"\u3060\u300d"]),
    144:("Setsuko",["\u300cI belong to the "+OB+L+CB,
                    "\u3000squad now, is this tidy?\u300d"]),
    146:("Setsuko",["\u300cThe "+OB+L+CB+" is our unit,",
                    "\u3000mid-sentence link ok?\u300d"]),
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
    rec=bytearray(banlz.decompress_all(bytes(stage))[1][1]); orig=len(rec)
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
