# -*- coding: utf-8 -*-
"""For every translated STAGE record, run apply_record() and diff the result
against the original decompressed record. Report every changed byte-range and
classify it: DIALOGUE (inside a row's [offset,offset+budget)) or OTHER (cue-heal
or corruption). OTHER ranges are shown with context to judge if apply_stage is
clobbering non-dialogue (event/deployment/cue) data."""
import glob, os, json
import apply_stage as A

recs = sorted(int(os.path.basename(p)[3:6]) for p in glob.glob(os.path.join(A.WORK,"tools","rec*_en.py")))
print("translated records:", len(recs))

grand_other = 0
for n in recs:
    dec = os.path.join(A.WORK,"analysis","stage_dec","rec%03d.bin"%n)
    js  = os.path.join(A.WORK,"analysis","rec%03d_script.json"%n)
    if not (os.path.exists(dec) and os.path.exists(js)):
        continue
    orig = open(dec,"rb").read()
    rows = json.load(open(js,encoding="utf-8"))
    import contextlib,io
    with contextlib.redirect_stdout(io.StringIO()):
        exp = A.apply_record(n)
    # diff into ranges
    ranges=[]; i=0; N=min(len(orig),len(exp))
    while i<N:
        if orig[i]!=exp[i]:
            s=i
            while i<N and orig[i]!=exp[i]: i+=1
            ranges.append((s,i))
        else: i+=1
    def in_row(a,b):
        for r in rows:
            o=r["offset"]; bud=r.get("budget",r["nbytes"])
            if o<=a and b<=o+bud: return True
        return False
    others=[(a,b) for a,b in ranges if not in_row(a,b)]
    if others or len(orig)!=len(exp):
        # find cue table location for context
        start,cnt = A.find_cue_table(bytearray(exp))
        print("rec%03d: %d ranges, %d OTHER  | len orig=%d exp=%d | cuetbl@0x%X x%d"
              % (n, len(ranges), len(others), len(orig), len(exp), start, cnt))
        for a,b in others[:12]:
            in_cue = start<=a<start+cnt*8
            ctx=orig[a:b]
            print("   OTHER 0x%05X-0x%05X (%dB) in_cuetbl=%s orig=%s"
                  % (a,b,b-a,in_cue,ctx[:12].hex(' ')))
        grand_other += len(others)
print("\nTOTAL non-dialogue changed ranges across all records:", grand_other)
