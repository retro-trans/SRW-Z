# -*- coding: utf-8 -*-
"""Link-gap diagnostic + final widths (in-game 31, scene 37).

Brackets each link tightly as x《term》y at three term lengths so we can read
the gap between the plain char and the link (and the underline extent). If the
side-gaps are constant regardless of term length -> fixed 《》 glyph padding; if
they scale -> content-driven cell.
"""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_linkdiag.bin")
ROWS = {7:(0x5710,66), 8:(0x5760,58), 9:(0x57a0,58),
        142:(0x84a0,31), 144:(0x84e0,95), 146:(0x8560,91)}


def bar(text, width):
    t = text[:width-1]
    return t + "." * (width-1-len(t)) + "|"


IG, SC = 31, 37
LINKDIAG = ["x《A》y one char here",
            "x《Glory Star》y ten",
            "x《Glory Star Squad》y"]
TESTS = {
    7:  ("Denzel", [bar("In-game final width 31", IG),
                    bar("Second line same width", IG),
                    bar("Third line on screen ok", IG)]),
    8:  ("Toby",   LINKDIAG),
    9:  ("Denzel", ["In-game width is now 31 wide,",
                    "does the last char show?"]),
    142:("Jerid",  [bar("Scene final width now 37", SC),
                    bar("Second line same width", SC),
                    bar("Third line in light panel", SC)]),
    144:("Setsuko",LINKDIAG),
    146:("Setsuko",["Scene width is now 37 wide,",
                    "all inside the light panel?"]),
}


def build_string(row):
    spk, lines = TESTS[row]
    return ("\n".join([spk]+lines)).encode("cp932") + b"\x00"


def replace_ptr(buf, oldp, newp):
    ob, nb, cnt, i = struct.pack("<I",oldp), struct.pack("<I",newp), 0, 0
    while True:
        j = buf.find(ob, i)
        if j < 0: break
        if j % 4 == 0: buf[j:j+4]=nb; cnt+=1; i=j+4
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
        off,nb=ROWS[r]; assert replace_ptr(rec, BASE+off, BASE+no[r])>=1
        for x in range(off,off+nb): rec[x]=0
    blob=banlz.compress_record(bytes(rec), flags)
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
