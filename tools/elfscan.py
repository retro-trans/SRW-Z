"""Locate LZ-decompressor candidates in the PS2 boot ELF by instruction signature.

A nibble-oriented LZ decoder must repeatedly: load bytes (lbu), split nibbles
(andi reg,reg,0xF and srl/sll by 4), and copy with small loops. Scan every
aligned 4-byte word in the executable segments, score sliding windows, then
disassemble the best hits for human reading.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN

path = sys.argv[1]
f = open(path, "rb")
elf = ELFFile(f)
print("machine: %s  entry: 0x%X" % (elf.header.e_machine, elf.header.e_entry))

segs = []
for seg in elf.iter_segments():
    if seg.header.p_type == "PT_LOAD" and seg.header.p_filesz > 0:
        segs.append((seg.header.p_vaddr, seg.header.p_offset, seg.header.p_filesz))
        print("PT_LOAD vaddr 0x%X  off 0x%X  filesz 0x%X"
              % (seg.header.p_vaddr, seg.header.p_offset, seg.header.p_filesz))

WINDOW = 96          # instructions per window
hits = []
for vaddr, off, size in segs:
    f.seek(off)
    data = f.read(size)
    n = len(data) // 4
    words = struct.unpack("<%dI" % n, data[:n * 4])

    # classify each instruction word
    feat = bytearray(n)   # bit0 andi 0xF, bit1 shift-by-4, bit2 lbu/lb, bit3 andi 0xFF
    for i, w in enumerate(words):
        op = w >> 26
        if op == 12:                      # andi
            imm = w & 0xFFFF
            if imm == 0xF:
                feat[i] |= 1
            elif imm == 0xFF:
                feat[i] |= 8
        elif op == 0:                     # SPECIAL: sll/srl
            funct = w & 0x3F
            sa = (w >> 6) & 0x1F
            if funct in (0, 2) and sa == 4 and w != 0:
                feat[i] |= 2
        elif op in (36, 32):              # lbu / lb
            feat[i] |= 4

    for i in range(0, n - WINDOW, 16):
        win = feat[i:i + WINDOW]
        a = sum(1 for x in win if x & 1)
        s = sum(1 for x in win if x & 2)
        l = sum(1 for x in win if x & 4)
        ff = sum(1 for x in win if x & 8)
        if a >= 2 and s >= 2 and l >= 6:
            score = a * 3 + s * 2 + l + ff
            hits.append((score, vaddr + i * 4, off + i * 4, a, s, l, ff))

# merge overlapping windows, keep the best
hits.sort(key=lambda h: h[1])
merged = []
for h in hits:
    if merged and h[1] - merged[-1][1] < WINDOW * 4:
        if h[0] > merged[-1][0]:
            merged[-1] = h
    else:
        merged.append(h)
merged.sort(key=lambda h: -h[0])

print("\n%d candidate region(s):" % len(merged))
for score, va, fo, a, s, l, ff in merged[:12]:
    print("  vaddr 0x%08X (file 0x%06X)  score %3d   andi0xF=%d shift4=%d lbu=%d andiFF=%d"
          % (va, fo, score, a, s, l, ff))

if len(sys.argv) > 2:
    target = int(sys.argv[2], 16)
    span = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x300
    for vaddr, off, size in segs:
        if vaddr <= target < vaddr + size:
            f.seek(off + (target - vaddr))
            code = f.read(span)
            md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
            print("\n=== DISASSEMBLY 0x%08X ===" % target)
            for ins in md.disasm(code, target):
                print("  %08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
