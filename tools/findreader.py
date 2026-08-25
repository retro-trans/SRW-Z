"""Find the 'read next SJIS char code' routine.

Signature: within a short window,
  - lbu (load a byte)
  - a compare/branch against 0x81 and 0xE0 (or 0x9F/0xEF) -- lead detection
  - sll by 8  (shift lead into high byte)
  - or        (combine with trail)
This is the canonical 1-or-2-byte character reader.
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

# per-instruction feature flags
LBU, SLL8, ORR, C81, CE0, C9F, CEF = (1 << i for i in range(7))
feat = [0] * n
for i, w in enumerate(words):
    op = w >> 26
    fn = w & 0x3F
    imm = w & 0xFFFF
    sa = (w >> 6) & 0x1F
    if op == 36:                                  # lbu
        feat[i] |= LBU
    elif op == 0 and fn == 0 and sa == 8 and w:   # sll r,r,8
        feat[i] |= SLL8
    elif op == 0 and fn == 37:                    # or
        feat[i] |= ORR
    elif op in (8, 9, 10, 11, 12, 24):            # addiu/slti/sltiu/andi ...
        if imm == 0x0081: feat[i] |= C81
        elif imm == 0x00E0: feat[i] |= CE0
        elif imm == 0x009F: feat[i] |= C9F
        elif imm == 0x00EF: feat[i] |= CEF
        elif imm == 0xFF7F: feat[i] |= C81   # addiu -0x81 counts as lead check
        elif imm == 0xFF20: feat[i] |= CE0

W = 40
res = []
for i in range(0, n - W, 4):
    agg = 0
    for j in range(i, i + W):
        agg |= feat[j]
    lead = bool(agg & (C81 | C9F)) and bool(agg & (CE0 | CEF))
    combine = bool(agg & SLL8) and bool(agg & ORR)
    if bool(agg & LBU) and (lead or (combine and (agg & (C81 | CE0)))):
        score = bin(agg).count("1") + (3 if lead and combine else 0)
        res.append((score, vbase + i * 4, agg))

# dedupe nearby
res.sort(key=lambda r: r[1])
merged = []
for r in res:
    if merged and r[1] - merged[-1][1] < W * 4:
        if r[0] > merged[-1][0]:
            merged[-1] = r
    else:
        merged.append(r)
merged.sort(key=lambda r: -r[0])

names = [("lbu", LBU), ("sll8", SLL8), ("or", ORR), ("0x81", C81),
         ("0xE0", CE0), ("0x9F", C9F), ("0xEF", CEF)]
print("%d candidate readers:" % len(merged))
for score, va, agg in merged[:20]:
    tags = " ".join(nm for nm, bit in names if agg & bit)
    print("  0x%08X  score %2d  [%s]" % (va, score, tags))
