# -*- coding: utf-8 -*-
"""Apply record N's English translation but SKIP a given set of row indices
(they stay Japanese). Isolates which rows break combat.

Usage: apply_skip.py <iso> <N> <skip1,skip2,...|range a-b>
"""
import sys, os, json, importlib.util
import apply_stage as A
import banlz

def main():
    iso = sys.argv[1]; n = int(sys.argv[2]); spec_skip = sys.argv[3]
    skip = set()
    for part in spec_skip.split(","):
        if "-" in part:
            a,b = part.split("-"); skip |= set(range(int(a), int(b)+1))
        elif part.strip():
            skip.add(int(part))
    # load T, remove skipped rows
    py = os.path.join(A.WORK,"tools","rec%03d_en.py"%n)
    sp = importlib.util.spec_from_file_location("r%d"%n, py)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    T = {k:v for k,v in m.T.items() if k not in skip}
    print("applying %d/%d rows (skipping %d)"%(len(T), len(m.T), len(m.T)-len(T)))
    # replicate apply_record with filtered T
    dec = os.path.join(A.WORK,"analysis","stage_dec","rec%03d.bin"%n)
    js  = os.path.join(A.WORK,"analysis","rec%03d_script.json"%n)
    orig = bytearray(open(dec,"rb").read())
    rows = json.load(open(js,encoding="utf-8"))
    exp = bytearray(orig)
    for idx,en in sorted(T.items()):
        r=rows[idx]; enc=en.encode("cp932"); bud=r.get("budget",r["nbytes"])
        if len(enc)>bud: continue
        off=r["offset"]; exp[off:off+bud]=enc+b"\x00"*(bud-len(enc))
    A.heal_cues(exp, rows)
    # splice
    stage=bytearray(open(os.path.join(A.WORK,"extracted","DATA_STAGE.BIN"),"rb").read())
    recs=banlz.decompress_all(stage)
    s1=recs[n][0]; s2=recs[n+1][0] if n+1<len(recs) else len(stage); slot=s2-s1
    blob=A.compress_cached(n, bytes(exp), slot)
    rt,_=banlz.decompress_record(blob,0); assert rt==bytes(exp)
    if len(blob)>slot:
        print("OVERSIZE skip"); return
    stage[s1:s2]=blob+b"\x00"*(slot-len(blob))
    with open(iso,"r+b") as f:
        f.seek(A.STAGE_LBA*A.SECTOR); f.write(bytes(stage))
    print("wrote STAGE: rec%03d english except rows %s"%(n, sorted(skip)[:20]))

if __name__=="__main__":
    main()
