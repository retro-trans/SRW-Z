"""Decisive test: are strings sequentially indexed (relocatable) or offset-based?

Take the full-English record, but GROW one early string so every string after
it shifts. If later lines still render correctly in-game, indexing is
sequential and fullwidth data is viable. If later lines garble, indexing is
offset-based and the renderer patch is required.

To keep offsets consistent for the rebuild, we operate on the raw decompressed
record and rebuild the whole null-terminated string region shifted.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rec001_en import T

work = r"E:\Projects\SRW Z\_work"
rows = json.load(open(os.path.join(work, "analysis", "rec001_script.json"), encoding="utf-8"))
rec = bytearray(open(os.path.join(work, "analysis", "stage_dec", "rec001.bin"), "rb").read())
stage = bytearray(open(os.path.join(work, "extracted", "DATA_STAGE.BIN"), "rb").read())

# apply full English in place first (same-size), so most lines are English
for idx, en in sorted(T.items()):
    r = rows[idx]
    enc = en.encode("cp932")
    if len(enc) <= r["nbytes"]:
        rec[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))

# Now GROW string index 15 by 16 bytes, shifting everything after it.
# String 15 speaker is Toby; we tag its visible text so we can spot it.
victim = rows[15]
voff, vlen = victim["offset"], victim["nbytes"]
old = rec[voff:voff + vlen].split(b"\x00")[0]
grown = b'Toby\n"GROWN LINE 15 marker!!"'          # deliberately longer
insert = len(grown) + 1 - vlen                     # net bytes added (incl. NUL)
print("victim idx15 at 0x%X: old %d bytes, new %d bytes, +%d shift"
      % (voff, vlen, len(grown) + 1, insert))

# rebuild record: [head..voff] + grown+NUL + [rest after old string]
rest_start = voff + vlen
newrec = bytearray(rec[:voff]) + grown + b"\x00" + bytearray(rec[rest_start:])
# keep the record the SAME total length so the record structure/size is stable:
# trim trailing padding by `insert` bytes if the tail is zeros, else keep (grows).
print("record: %d -> %d bytes" % (len(rec), len(newrec)))

SLOT_START, SLOT_END = 0x00D860, 0x011AE0
total, flags, _ = banlz.parse_header(bytes(stage), SLOT_START)
blob = banlz.compress_record(bytes(newrec), flags)
assert banlz.decompress_record(blob)[0] == bytes(newrec)
slot = SLOT_END - SLOT_START
print("recompressed %d / slot %d -> %s"
      % (len(blob), slot, "FITS" if len(blob) <= slot else "TOO BIG"))
assert len(blob) <= slot
stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
assert all(r[1] is not None for r in banlz.decompress_all(bytes(stage)))
open(os.path.join(work, "patched", "DATA_STAGE.BIN"), "wb").write(stage)
print("written grow-test STAGE.BIN — watch idx15 (grown) and later lines")
