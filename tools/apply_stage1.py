"""Build the stage-1 English patch end to end.

1. Patch English into the decompressed rec001 (in place, byte-budget checked)
2. Recompress with the game's own flags
3. Verify: decompress(new blob) == patched record, blob fits the slot
4. Splice into DATA/STAGE.BIN (zero-fill the remainder of the slot)
5. Verify the container still parses record-for-record
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

# Strings the first dump missed (they contain cp932 NEC extensions like the
# Roman numeral II in "Gundam Mk-II", which strict shift_jis rejects).
# Keyed by exact offset in the decompressed record: (byte_budget, english)
EXTRA = {
    0x5B30: (103, 'Roberto\n"We used Capt. Quattro and the\n Gundam Mk-II as bait. The Titans\n snapped it right up."'),
    0x5C30: (68,  'Roberto\n"After the Mk-II, we\'ll help\n ourselves to these too."'),
    0x67D0: (64,  '$n\n"But shouldn\'t the Gundam Mk-II\n be in Titans colors...?"'),
    0x6C70: (64,  '$n\n"The Gundam Mk-II belongs to the\n Federation! Give it back!"'),
    0x8650: (13,  '$n\n"......"'),
    0x95A0: (17,  '$n\n"**, ****..."'),
    0xB090: (9,   '$n\n"...!"'),
    0xB250: (6,   "???"),
}

# --- 1. patch strings in place ---
applied, over = 0, []
for idx, en in sorted(T.items()):
    r = rows[idx]
    enc = en.encode("shift_jis")
    if len(enc) > r["nbytes"]:
        over.append((idx, len(enc), r["nbytes"], en))
        continue
    off = r["offset"]
    rec[off:off + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))
    applied += 1

for off, (budget, en) in sorted(EXTRA.items()):
    enc = en.encode("cp932")
    if len(enc) > budget:
        over.append(("0x%X" % off, len(enc), budget, en))
        continue
    # sanity: must overwrite a null-terminated string of exactly this budget
    assert rec[off + budget] == 0 or budget == 6, "bad EXTRA offset 0x%X" % off
    rec[off:off + budget] = enc + b"\x00" * (budget - len(enc))
    applied += 1

print("strings applied: %d / %d" % (applied, len(T) + len(EXTRA)))
if over:
    print("OVER BUDGET: %d" % len(over))
    for idx, got, budget, en in over:
        print("  [%03d] %d > %d : %s" % (idx, got, budget, en.replace(chr(10), " / ")[:70]))
    sys.exit(1)

# --- 2/3. recompress and verify ---
SLOT_START, SLOT_END = 0x00D860, 0x011AE0
total, flags, _ = banlz.parse_header(bytes(stage), SLOT_START)
assert total == len(rec), "record length changed?!"
blob = banlz.compress_record(bytes(rec), flags)
rt, _ = banlz.decompress_record(blob)
assert rt == bytes(rec), "codec round-trip failed on patched record"
slot = SLOT_END - SLOT_START
print("recompressed: %s bytes (slot %s)  -> %s"
      % ("{:,}".format(len(blob)), "{:,}".format(slot),
         "FITS" if len(blob) <= slot else "TOO BIG"))
if len(blob) > slot:
    sys.exit(1)

# --- 4. splice ---
stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))

# --- 5. whole-container verification ---
recs = banlz.decompress_all(bytes(stage))
bad = [r for r in recs if r[1] is None]
print("container re-parse: %d records, %d errors" % (len(recs), len(bad)))
ok = recs[1][1] == bytes(rec)
print("record 1 decompresses to patched content: %s" % ok)
if bad or not ok:
    sys.exit(1)

out = os.path.join(work, "patched", "DATA_STAGE.BIN")
open(out, "wb").write(stage)
print("\nwritten %s (%s bytes, size %s)"
      % (out, "{:,}".format(len(stage)),
         "unchanged" if len(stage) == 3910128 else "CHANGED!"))

# quick taste of the patched text
i = rec.find(b"Denzel\n")
print("\nsample: %r" % rec[i:i + 90].split(b"\x00")[0].decode("shift_jis"))
