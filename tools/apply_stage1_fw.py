"""Diagnostic build: encode Stage 1 strings as FULLWIDTH (2-byte SJIS) where
they fit the byte budget; leave the rest as the original Japanese.

Purpose: prove whether the dialogue font renders fullwidth Latin. Katakana
name plates already render, so if fullwidth English shows up, the font is fine
and the real fix is an ASCII->fullwidth remap. If it is ALSO blank, the
problem is elsewhere.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rec001_en import T


def to_fullwidth(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == " ":
            out.append("\u3000")
        elif ch == "\n":
            out.append("\n")
        elif 0x21 <= o <= 0x7E:
            out.append(chr(o + 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


work = r"E:\Projects\SRW Z\_work"
rows = json.load(open(os.path.join(work, "analysis", "rec001_script.json"), encoding="utf-8"))
rec = bytearray(open(os.path.join(work, "analysis", "stage_dec", "rec001.bin"), "rb").read())
stage = bytearray(open(os.path.join(work, "extracted", "DATA_STAGE.BIN"), "rb").read())

applied = fit = 0
for idx, en in sorted(T.items()):
    r = rows[idx]
    fw = to_fullwidth(en)
    enc = fw.encode("cp932")
    if len(enc) > r["nbytes"]:
        continue                      # leave original Japanese
    rec[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))
    applied += 1
    if idx in (7, 8, 9, 142, 143):    # first corridor/battle lines
        fit += 1

print("fullwidth strings that fit: %d / %d" % (applied, len(T)))

SLOT_START, SLOT_END = 0x00D860, 0x011AE0
total, flags, _ = banlz.parse_header(bytes(stage), SLOT_START)
blob = banlz.compress_record(bytes(rec), flags)
rt, _ = banlz.decompress_record(blob)
assert rt == bytes(rec), "round-trip failed"
slot = SLOT_END - SLOT_START
print("recompressed %d bytes / slot %d -> %s"
      % (len(blob), slot, "FITS" if len(blob) <= slot else "TOO BIG"))
assert len(blob) <= slot
stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))

recs = banlz.decompress_all(bytes(stage))
assert all(r[1] is not None for r in recs) and recs[1][1] == bytes(rec)
open(os.path.join(work, "patched", "DATA_STAGE.BIN"), "wb").write(stage)
print("written patched/DATA_STAGE.BIN (fullwidth diagnostic)")
