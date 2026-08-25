# -*- coding: utf-8 -*-
"""Rebuild DATA_STAGE.BIN into a target ISO with a chosen variation, to isolate
what in apply_stage breaks combat.

Usage: build_stage_variant.py <iso> <mode>
  mode = noheal   -> apply English text but DISABLE heal_cues (original cue ptrs)
  mode = textonly -> same as noheal (alias)
  mode = full     -> normal apply (text + heal) [control]
"""
import glob, os, sys, json
import apply_stage as A

def main():
    iso_path = sys.argv[1]
    mode = sys.argv[2]
    if mode in ("noheal","textonly"):
        A.heal_cues = lambda exp, rows: None   # disable cue healing
        print("heal_cues DISABLED")
    recs_ids = sorted(int(os.path.basename(p)[3:6]) for p in glob.glob(os.path.join(A.WORK,"tools","rec*_en.py")))
    stage = bytearray(open(os.path.join(A.WORK,"extracted","DATA_STAGE.BIN"),"rb").read())
    allrecs = A.banlz.decompress_all(stage)
    applied=skipped=0
    for n in recs_ids:
        try:
            exp = A.apply_record(n)
        except Exception as e:
            print("rec%03d apply failed: %s"%(n,e)); continue
        s1 = allrecs[n][0]
        s2 = allrecs[n+1][0] if n+1 < len(allrecs) else len(stage)
        slot = s2 - s1
        blob = A.compress_cached(n, exp, slot)
        rt,_ = A.banlz.decompress_record(blob,0)
        assert rt==exp, "roundtrip fail rec%d"%n
        if len(blob) > slot:
            skipped += 1
            continue
        stage[s1:s2] = blob + b"\x00"*(slot-len(blob))
        applied += 1
    with open(iso_path,"r+b") as iso:
        iso.seek(A.STAGE_LBA*A.SECTOR)
        iso.write(bytes(stage))
    print("mode=%s applied=%d skipped=%d STAGE written to %s"%(mode,applied,skipped,iso_path))

if __name__=="__main__":
    main()
