"""Minimal font diagnostic: keep rec001 as original Japanese, but overwrite a
few early lines with fullwidth Latin test strings that fit their budgets.
Reaching the corridor scene shows whether fullwidth Latin renders."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz


def fw(s):
    return "".join("\u3000" if c == " " else
                   (chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c)
                   for c in s)


work = r"E:\Projects\SRW Z\_work"
sys.path.insert(0, os.path.join(work, "tools"))
from rec001_en import T

rows = json.load(open(os.path.join(work, "analysis", "rec001_script.json"), encoding="utf-8"))
rec = bytearray(open(os.path.join(work, "analysis", "stage_dec", "rec001.bin"), "rb").read())
stage = bytearray(open(os.path.join(work, "extracted", "DATA_STAGE.BIN"), "rb").read())

# start from the full English build (which is known to fit the slot)
for idx, en in sorted(T.items()):
    r = rows[idx]
    enc = en.encode("cp932")
    if len(enc) > r["nbytes"]:
        continue
    rec[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))

# override two early lines with FULLWIDTH Latin as the render test
TESTS = {
    142: "\u30b8\u30a7\u30ea\u30c9\n" + fw("HEY YOU"),          # Jerid, fullwidth body
    143: fw("Denzel") + "\n" + fw("TEST"),                      # fullwidth incl. name
}
for idx, txt in TESTS.items():
    r = rows[idx]
    enc = txt.encode("cp932")
    assert len(enc) <= r["nbytes"], "idx %d too big: %d>%d" % (idx, len(enc), r["nbytes"])
    rec[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))
    print("idx %d -> %r (%d/%d bytes)" % (idx, txt.replace("\n", "\\n"), len(enc), r["nbytes"]))

SLOT_START, SLOT_END = 0x00D860, 0x011AE0
total, flags, _ = banlz.parse_header(bytes(stage), SLOT_START)
blob = banlz.compress_record(bytes(rec), flags)
assert banlz.decompress_record(blob)[0] == bytes(rec)
slot = SLOT_END - SLOT_START
print("recompressed %d / slot %d" % (len(blob), slot))
assert len(blob) <= slot
stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
assert all(r[1] is not None for r in banlz.decompress_all(bytes(stage)))
open(os.path.join(work, "patched", "DATA_STAGE.BIN"), "wb").write(stage)
print("written fullwidth-test STAGE.BIN")
