# -*- coding: utf-8 -*-
"""Rebuild STAGE with record N recompressed but UNCHANGED (no text edits, no cue
heal). If combat then breaks, the game's decompressor mis-decodes our re-packed
blob (compressor incompatibility); if it's fine, the break is the English text.

Usage: recompress_test.py <iso> <N>
"""
import sys, os
import apply_stage as A
import banlz

def main():
    iso = sys.argv[1]; n = int(sys.argv[2])
    stage = bytearray(open(os.path.join(A.WORK,"extracted","DATA_STAGE.BIN"),"rb").read())
    recs = banlz.decompress_all(stage)
    exp = open(os.path.join(A.WORK,"analysis","stage_dec","rec%03d.bin"%n),"rb").read()
    s1 = recs[n][0]; s2 = recs[n+1][0] if n+1<len(recs) else len(stage)
    slot = s2 - s1
    blob = A.compress_cached(n, exp, slot)
    rt,_ = banlz.decompress_record(blob,0)
    assert rt==exp, "roundtrip fail"
    # is our recompressed blob byte-identical to the game's original blob?
    orig_blob = bytes(stage[s1:s2]).rstrip(b"\x00")
    print("rec%03d: our blob=%d bytes, orig slot content(=trimmed)=%d, slot=%d, identical=%s"
          % (n, len(blob), len(orig_blob), slot, blob==bytes(stage[s1:s1+len(blob)])))
    if len(blob) > slot:
        print("  OVERSIZE, would skip"); return
    stage[s1:s2] = blob + b"\x00"*(slot-len(blob))
    with open(iso,"r+b") as f:
        f.seek(A.STAGE_LBA*A.SECTOR); f.write(bytes(stage))
    print("  wrote STAGE with rec%03d recompressed-unchanged"%n)

if __name__=="__main__":
    main()
