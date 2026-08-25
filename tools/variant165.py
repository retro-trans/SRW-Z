"""Build srwz_test.bin with a custom string for row 165. Usage:
variant165.py <mode>   mode: en | jpname | jpquotes | fullwidth | jp
"""
import sys, os, json, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

mode = sys.argv[1]
# 'pristine' = byte-identical original rec001 (no T, no EXTRA, no cue heal):
# the one configuration that isolates ELF vs rec001-data as the hang trigger.
# 'half:N-M' = apply ONLY T rows N..M (plus cue heal) for region bisection.
V = {
    "en":        'Emma\n"What are you two doing?"',
    "jpname":    'エマ\n"What are you two doing?"',
    "jpquotes":  'エマ\n「What are you two doing?」',
    "fullwidth": 'エマ\n「Ｄｏｉｎｇ　ｗｈａｔ？」',
    "even":      'エマ\n「What are you two doing」',
    "evenq":     'エマ\n"What are you two doing?!"',
    "exact33":   'Emma\n"What are you two doing...?"',
    "jp":        None,   # keep original
}.get(mode)
lo, hi = 0, 10**9
if mode == "pristine":
    lo, hi = -1, -1                    # apply nothing
elif mode.startswith("half:"):
    a, b = mode[5:].split("-")
    lo, hi = int(a), int(b)

# 'fontdump': row 139 (641B slot) displays every fullwidth char whose cell we
# want to rip from the live master font (native-font atlas project): the
# demand-decoder fills 0x9AE610 cells as the line renders, then pine dumps them.
FONTDUMP = ("．＂＇！，－？" +
            "".join(chr(0xFF10 + i) for i in range(10)) +
            "".join(chr(0xFF21 + i) for i in range(26)) +
            "".join(chr(0xFF41 + i) for i in range(26)))

work = r"E:\Projects\SRW Z\_work"
rows = json.load(open(work + r"\analysis\rec001_script.json", encoding="utf-8"))
orig = bytearray(open(work + r"\analysis\stage_dec\rec001.bin", "rb").read())
spec = importlib.util.spec_from_file_location('r1', 'rec001_en.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

exp = bytearray(orig)
for idx, en in sorted(m.T.items()):
    if not (lo <= idx <= hi):
        continue
    if idx == 165 and V is not None:
        en = V
    r = rows[idx]
    enc = en.encode("cp932")
    if len(enc) > r["nbytes"]:
        print("OVER at", idx, len(enc), ">", r["nbytes"]); continue
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
if mode != "pristine":
    for off, (budget, en) in EXTRA.items():
        enc = en.encode("cp932")
        if len(enc) <= budget:
            exp[off:off + budget] = enc + b"\x00" * (budget - len(enc))

if mode == "fontdump":
    r = rows[139]
    enc = FONTDUMP.encode("cp932")
    # break into 3 display lines so nothing clips off-window
    third = (len(FONTDUMP) // 3) * 2
    enc = (FONTDUMP[:23] + "\n" + FONTDUMP[23:46] + "\n" + FONTDUMP[46:]).encode("cp932")
    assert len(enc) <= r["nbytes"], (len(enc), r["nbytes"])
    exp[r["offset"]:r["offset"] + r["nbytes"]] = enc + b"\x00" * (r["nbytes"] - len(enc))
    print("fontdump row139: %d chars, %d bytes" % (len(FONTDUMP), len(enc)))

# --- SE-cue table heal (the "...I am..." soft-lock root cause) ---
# Table at +0x2890: [u32 ptr(0x750000+off), u32 id]. Each cue fires when the
# text printer reaches ptr (deltas are 16-aligned blocks). If the English
# replacement is SHORTER than the cue's delta the cue never fires and the SE
# sequencer stalls -> dialogue advance soft-locks a few lines later (music
# keeps playing). Heal: retarget any uncovered cue to the last 16-aligned
# block the translated string still covers.
import struct as _st
toff = 0x2890
healed = 0
while True:
    ptr, sid = _st.unpack_from("<II", exp, toff)
    if not (0x750000 <= ptr < 0x750000 + len(exp)):
        break
    o = ptr - 0x750000
    for r in rows:
        if r["offset"] <= o < r["offset"] + r["nbytes"]:
            base = r["offset"]
            end = exp.index(b"\x00", base)
            enlen = end - base
            if enlen <= o - base:            # printer never reaches the cue
                nd = max(0, ((enlen - 8) // 16) * 16)
                _st.pack_into("<I", exp, toff, 0x750000 + base + nd)
                print("cue id=%#x healed: +%#x -> +%#x (enlen %d)"
                      % (sid, o - base, nd, enlen))
                healed += 1
            break
    toff += 8
print("cue table: %d entries retargeted" % healed)

stage = bytearray(open(work + r"\extracted\DATA_STAGE.BIN", "rb").read())
if mode == "pristine":
    # keep the factory-compressed record byte-identical (our compressor is
    # weaker than the original and pristine text doesn't fit the slot)
    rt, _ = banlz.decompress_record(bytes(stage), banlz.decompress_all(stage)[1][0])
    assert rt == bytes(exp), "extracted DATA_STAGE.BIN rec1 is not pristine!"
else:
    recs = banlz.decompress_all(stage)
    s1, s2 = recs[1][0], recs[2][0]
    blob = banlz.compress_record(bytes(exp))
    rt, _ = banlz.decompress_record(blob, 0)
    assert rt == bytes(exp)
    slot = s2 - s1
    assert len(blob) <= slot
    stage[s1:s2] = blob + b"\x00" * (slot - len(blob))
SECTOR, LBA = 2048, 1651029
with open(work + r"\iso\srwz_test.bin", "r+b") as iso:
    iso.seek(LBA * SECTOR)
    iso.write(bytes(stage))
print("variant '%s' written: row165 = %r" % (mode, V))
