"""Locate SJIS lead-byte handling code in the ELF.

A Shift-JIS decoder must classify bytes into the lead ranges 0x81-0x9F /
0xE0-0xEF and convert (lead, trail) into a glyph index. That leaves
fingerprints: addiu/slti immediates -0x81 (0xFF7F), -0xE0 (0xFF20),
range widths 0x1F/0x10/0x60, trail math -0x40 (0xFFC0).
Score 64-instruction windows by how many fingerprints they contain.
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

# immediate fingerprints, weighted
IMM_SCORES = {
    0xFF7F: 4,   # addiu r, r, -0x81
    0xFF61: 3,   # addiu -0x9F
    0xFF20: 3,   # addiu -0xE0
    0xFFC0: 2,   # addiu -0x40   (trail base)
    0xFF81: 2,
    0x001F: 1,   # sltiu range width for 0x81..0x9F
    0x0081: 2, 0x009F: 2, 0x00E0: 1, 0x00EF: 2, 0x00FC: 2,
}

feat = [0] * n
for i, w in enumerate(words):
    op = w >> 26
    if op in (8, 9, 10, 11, 12, 14):        # addi/addiu/slti/sltiu/andi/xori
        imm = w & 0xFFFF
        if imm in IMM_SCORES:
            feat[i] = IMM_SCORES[imm]

W = 64
hits = []
for i in range(0, n - W, 16):
    s = sum(feat[i:i + W])
    if s >= 8:
        hits.append((s, vbase + i * 4))

hits.sort(key=lambda h: h[1])
merged = []
for s, va in hits:
    if merged and va - merged[-1][1] < W * 4:
        if s > merged[-1][0]:
            merged[-1] = (s, merged[-1][1])
    else:
        merged.append((s, va))
merged.sort(key=lambda h: -h[0])

print("%d clusters:" % len(merged))
for s, va in merged[:20]:
    # show which immediates appear in the window
    i0 = (va - vbase) // 4
    imms = {}
    for w in words[i0:i0 + W]:
        if (w >> 26) in (8, 9, 10, 11, 12, 14):
            imm = w & 0xFFFF
            if imm in IMM_SCORES:
                imms[imm] = imms.get(imm, 0) + 1
    print("  0x%08X  score %3d  %s"
          % (va, s, " ".join("%04X:%d" % kv for kv in sorted(imms.items()))))
