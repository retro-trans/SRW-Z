"""Rebuild rec001 with selected string indices REVERTED to original Japanese,
recompress, and splice into srwz_test.bin. Usage: bisect164.py [idx ...]"""
import sys, os, json, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

REVERT = set(int(a) for a in sys.argv[1:]) or {164}
work = r"E:\Projects\SRW Z\_work"
rows = json.load(open(work + r"\analysis\rec001_script.json", encoding="utf-8"))
orig = bytearray(open(work + r"\analysis\stage_dec\rec001.bin", "rb").read())
spec = importlib.util.spec_from_file_location('r1', 'rec001_en.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

exp = bytearray(orig)
for idx, en in sorted(m.T.items()):
    if idx in REVERT:
        continue
    r = rows[idx]
    enc = en.encode("shift_jis")
    if len(enc) > r["nbytes"]:
        continue
    off = r["offset"]
    exp[off:off + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))

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
for off, (budget, en) in EXTRA.items():
    enc = en.encode("cp932")
    if len(enc) <= budget:
        exp[off:off + budget] = enc + b"\x00" * (budget - len(enc))

stage = bytearray(open(work + r"\extracted\DATA_STAGE.BIN", "rb").read())
recs = banlz.decompress_all(stage)
s1, s2 = recs[1][0], recs[2][0]
blob = banlz.compress_record(bytes(exp))
rt, _ = banlz.decompress_record(blob, 0)
assert rt == bytes(exp), "roundtrip mismatch"
slot = s2 - s1
assert len(blob) <= slot, (len(blob), slot)
stage[s1:s2] = blob + b"\x00" * (slot - len(blob))
SECTOR, LBA = 2048, 1651029
with open(work + r"\iso\srwz_test.bin", "r+b") as iso:
    iso.seek(LBA * SECTOR)
    iso.write(bytes(stage))
print("bisect ISO written; reverted:", sorted(REVERT))
