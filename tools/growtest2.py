"""Decisive visible grow-test.

Make three consecutive corridor lines FULLWIDTH (visible), and make the first
of them GROW beyond its original byte length (shifting the two after it).
If all three render correct, legible text in order, string indexing is
sequential and fullwidth data is viable with no code patch.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rec001_en import T


def fw(s):
    return "".join("\u3000" if c == " " else
                   (chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c)
                   for c in s)


work = r"E:\Projects\SRW Z\_work"
rows = json.load(open(os.path.join(work, "analysis", "rec001_script.json"), encoding="utf-8"))
rec = bytearray(open(os.path.join(work, "analysis", "stage_dec", "rec001.bin"), "rb").read())
stage = bytearray(open(os.path.join(work, "extracted", "DATA_STAGE.BIN"), "rb").read())

# Build the string region fresh so growth is clean. Strategy: apply English
# in-place everywhere, then splice-grow three corridor lines as fullwidth.
for idx, en in sorted(T.items()):
    r = rows[idx]
    enc = en.encode("cp932")
    if len(enc) <= r["nbytes"]:
        rec[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))

# Corridor lines 142,143,144. Make them fullwidth; GROW 142 well past its
# original 31-byte budget so 143/144 must shift.
NEW = {
    142: "\u30b8\u30a7\u30ea\u30c9\n" + fw("GROWN WIDE LINE ONE TWO THREE"),  # >> 31 bytes
    143: "\u30bb\u30c4\u30b3\n" + fw("SECOND LINE HERE"),
    144: "\u30c8\u30d3\u30fc\n" + fw("THIRD LINE OK"),
}

# Rebuild by processing strings in offset order, growing where needed.
# Collect original (offset, nbytes) for the three, splice sequentially.
targets = sorted(NEW.keys(), key=lambda i: rows[i]["offset"])
out = bytearray()
cur = 0
for idx in targets:
    r = rows[idx]
    off, ln = r["offset"], r["nbytes"]
    out += rec[cur:off]                       # unchanged bytes up to this string
    out += NEW[idx].encode("cp932") + b"\x00"  # grown replacement (+NUL)
    cur = off + ln                            # skip original string+its NUL region
out += rec[cur:]
rec = out
print("record grew to %d bytes (was 45968)" % len(rec))

SLOT_START, SLOT_END = 0x00D860, 0x011AE0
total, flags, _ = banlz.parse_header(bytes(stage), SLOT_START)
blob = banlz.compress_record(bytes(rec), flags)
assert banlz.decompress_record(blob)[0] == bytes(rec)
slot = SLOT_END - SLOT_START
print("recompressed %d / slot %d -> %s"
      % (len(blob), slot, "FITS" if len(blob) <= slot else "TOO BIG"))
assert len(blob) <= slot
stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
assert all(r[1] is not None for r in banlz.decompress_all(bytes(stage)))
open(os.path.join(work, "patched", "DATA_STAGE.BIN"), "wb").write(stage)
print("written visible grow-test — corridor lines 142/143/144 fullwidth, 142 grown")
