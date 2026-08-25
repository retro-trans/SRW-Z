# -*- coding: utf-8 -*-
"""Width 33/37 + 「」 quotes + link fullwidth test + speaker-name color A/B."""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_poc4.bin")
ROWS = {7:(0x5710,66), 8:(0x5760,58), 9:(0x57a0,58),
        142:(0x84a0,31), 144:(0x84e0,95), 146:(0x8560,91)}

def fw(s):
    out=[]
    for c in s:
        o=ord(c)
        out.append(chr(o+0xFEE0) if 0x21<=o<=0x7E else ('\u3000' if c==' ' else c))
    return ''.join(out)

TESTS = {
    # in-game, English name -> is it blue?  + 「」 quotes + width 33
    7:  ("Denzel", ["「In-game at width thirty-three now,",
                    "\u3000corner-bracket quotes here,",
                    "\u3000is THIS (English) name blue?」"]),
    # in-game link: half vs fullwidth term
    8:  ("Toby",   ["half x\u300aGlory Star\u300by",
                    "full x\u300a"+fw("Glory Star")+"\u300by",
                    "does full fill the underline?"]),
    # in-game, JAPANESE name text -> is THAT blue? (same box, isolates color rule)
    9:  ("\u30c7\u30f3\u30bc\u30eb", ["「Speaker name above is JP",
                    "\u3000\u30c7\u30f3\u30bc\u30eb -- is this one blue?」"]),
    # scene, English name + 「」 + width 37
    142:("Jerid",  ["「Scene box at width thirty-seven,",
                    "\u3000corner brackets, English name.」"]),
    # scene link: half vs fullwidth
    144:("Setsuko",["half x\u300aGlory Star\u300by",
                    "full x\u300a"+fw("Glory Star")+"\u300by",
                    "which link looks tidiest?"]),
    # scene, JAPANESE name text
    146:("\u30bb\u30c4\u30b3", ["「Speaker name above is JP",
                    "\u3000\u30bb\u30c4\u30b3 -- is this one blue?」"]),
}

def build_string(row):
    spk, lines = TESTS[row]
    return ("\n".join([spk]+lines)).encode("cp932") + b"\x00"

def replace_ptr(buf, oldp, newp):
    ob,nb,cnt,i=struct.pack("<I",oldp),struct.pack("<I",newp),0,0
    while True:
        j=buf.find(ob,i)
        if j<0: break
        if j%4==0: buf[j:j+4]=nb; cnt+=1; i=j+4
        else: i=j+1
    return cnt

def main():
    with open(BASE_ISO,"rb") as f:
        f.seek(STAGE_LBA*SECTOR); stage=bytearray(f.read(STAGE_SIZE))
    rec=bytearray(banlz.decompress_all(bytes(stage))[1][1]); orig=len(rec)
    total, flags, at = banlz.parse_header(bytes(stage), SLOT_START)
    no={}
    for r in sorted(TESTS): no[r]=len(rec); rec+=build_string(r)
    for r in sorted(TESTS):
        off,nb=ROWS[r]; assert replace_ptr(rec,BASE+off,BASE+no[r])>=1
        for x in range(off,off+nb): rec[x]=0
    blob=banlz.compress_record(bytes(rec),flags)
    assert banlz.decompress_record(blob)[0]==bytes(rec)
    slot=SLOT_END-SLOT_START
    print("rec %d->%d; blob %d / slot %d -> %s"%(orig,len(rec),len(blob),slot,
          "FITS" if len(blob)<=slot else "TOO BIG"))
    assert len(blob)<=slot
    stage[SLOT_START:SLOT_END]=blob+b"\x00"*(slot-len(blob))
    assert banlz.decompress_all(bytes(stage))[1][1]==bytes(rec)
    import banlz_strict as bs
    t2,fl2,at2=banlz.parse_header(bytes(stage),SLOT_START)
    print("strict:",len(bs.verify(bytes(stage),at2,t2)[1]))
    shutil.copyfile(BASE_ISO,OUT_ISO)
    with open(OUT_ISO,"r+b") as f: f.seek(STAGE_LBA*SECTOR); f.write(stage)
    print("wrote",OUT_ISO)

if __name__=="__main__": main()
