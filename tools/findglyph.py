"""Find the SJIS->glyph-index converter by its near-unique fingerprint:
the trail-byte 0x7F gap skip (JIS conversion) plus lead-range handling.

The converter does, roughly:
  lead -= 0x81 (or 0xE0 fold); if trail > 0x7F: trail -= 1; trail -= 0x40;
  index = lead*N + trail   (N = chars-per-row)
Signature within a window: compare/sub against 0x7F or 0x40 AND a lead
constant (0x81/0xE0/0x9F) AND a multiply (mult/mflo) or a shift-add index.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile

path = sys.argv[1]
f = open(path, "rb")
elf = ELFFile(f)
seg = [s for s in elf.iter_segments()
       if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
vbase = seg.header.p_vaddr
f.seek(seg.header.p_offset)
data = f.read(seg.header.p_filesz)
n = len(data) // 4
words = struct.unpack("<%dI" % n, data[:n * 4])

GAP7F, C40, LEAD, MULT, C1F, C5E, CBC = (1 << i for i in range(7))
feat = [0] * n
for i, w in enumerate(words):
    op = w >> 26
    fn = w & 0x3F
    imm = w & 0xFFFF
    if op in (8, 9, 10, 11, 12, 13, 14):     # imm ops
        if imm in (0x007F, 0x0080, 0xFF80, 0xFF81):
            feat[i] |= GAP7F
        elif imm in (0x0040, 0xFFC0):
            feat[i] |= C40
        elif imm in (0x0081, 0x00E0, 0x009F, 0x00EF, 0xFF7F, 0xFF20):
            feat[i] |= LEAD
        elif imm == 0x001F:
            feat[i] |= C1F
        elif imm == 0x005E:
            feat[i] |= C5E
        elif imm in (0x00BC, 0x00BB):
            feat[i] |= CBC
    elif op == 0 and fn in (0x18, 0x19, 0x1C, 0x1D):   # mult/multu/div..
        feat[i] |= MULT
    elif op == 0x1C:                          # MMI mult variants (EE)
        feat[i] |= MULT

W = 48
hits = []
for i in range(0, n - W, 4):
    agg = 0
    for j in range(i, i + W):
        agg |= feat[j]
    # require the gap skip AND a lead check AND (trail-0x40 or a row-width const)
    if (agg & GAP7F) and (agg & LEAD) and (agg & (C40 | C5E | CBC | MULT)):
        score = bin(agg).count("1")
        hits.append((score, vbase + i * 4, agg))

hits.sort(key=lambda h: h[1])
merged = []
for h in hits:
    if merged and h[1] - merged[-1][1] < W * 4:
        if h[0] > merged[-1][0]:
            merged[-1] = h
    else:
        merged.append(h)
merged.sort(key=lambda h: -h[0])

nm = [("gap7F", GAP7F), ("-0x40", C40), ("lead", LEAD), ("mult", MULT),
      ("0x1F", C1F), ("0x5E", C5E), ("0xBC", CBC)]
print("%d glyph-index candidates:" % len(merged))
for score, va, agg in merged[:20]:
    print("  0x%08X  [%s]" % (va, " ".join(t for t, b in nm if agg & b)))
