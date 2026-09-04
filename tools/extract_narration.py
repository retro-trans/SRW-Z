# -*- coding: utf-8 -*-
import sys, io, os, struct, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "tools")
import banlz
from mtvpros_en import TEXTS
src=open("extracted/DATA_MTV_PROS.BIN","rb").read()
recs=banlz.decompress_all(src)
queue=list(TEXTS); rows=[]
for ri,(s0,dat) in enumerate(recs):
    dat=bytearray(dat); j=0
    while True:
        j=dat.find(b"rawt",j)
        if j<0: break
        size=struct.unpack_from("<I",dat,j+4)[0]
        jp_raw=bytes(dat[j+8:j+8+size])
        jp_txt=jp_raw.decode("cp932","replace")
        jp_prefix,en=queue.pop(0)
        assert jp_raw.startswith(jp_prefix.encode("cp932")),"order mismatch rec%d"%ri
        rows.append({"key":"mtv_r%02d_%05x"%(ri,j),"jp":jp_txt,"en":en,
                     "lines":jp_txt.count(chr(10))+1,"jp_bytes":size})
        j+=8+size
print("extracted %d narration chunks" % len(rows))
json.dump(rows, io.open("analysis/narration_sheet.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows[:3]:
    print(" %s (%d lines, %d jp bytes)" % (r["key"],r["lines"],r["jp_bytes"]))
    print("   JP:", r["jp"][:40].replace(chr(10),"/"))
    print("   EN:", r["en"][:50].replace(chr(10),"/"))
