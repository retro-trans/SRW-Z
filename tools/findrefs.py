"""Find filename strings in the ELF, then find the MIPS code that references
their addresses via lui/addiu (or lui/ori) pairs.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile

path = sys.argv[1]
needles = [n.encode("ascii") for n in sys.argv[2:]]

f = open(path, "rb")
elf = ELFFile(f)
seg = [s for s in elf.iter_segments()
       if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
vbase = seg.header.p_vaddr
f.seek(seg.header.p_offset)
data = f.read(seg.header.p_filesz)

targets = []
for nd in needles:
    pos = data.find(nd)
    while pos != -1:
        # widen to the whole null-terminated string for context
        s0 = pos
        while s0 > 0 and data[s0 - 1] != 0:
            s0 -= 1
        s1 = data.find(b"\x00", pos)
        full = data[s0:s1].decode("ascii", "replace")
        va = vbase + s0
        targets.append((va, full))
        print("string %-28r at vaddr 0x%08X" % (full, va))
        pos = data.find(nd, pos + 1)

n = len(data) // 4
words = struct.unpack("<%dI" % n, data[:n * 4])

# collect lui values per register, then match the following addiu/ori
print("\n=== CODE REFERENCES ===")
for tva, tname in targets:
    hi_a = (tva + 0x8000) >> 16          # lui for addiu (signed low)
    lo_a = tva & 0xFFFF
    hi_o = tva >> 16                     # lui for ori (unsigned low)
    refs = []
    for i, w in enumerate(words):
        op = w >> 26
        if op == 15:                     # lui rt, imm
            imm = w & 0xFFFF
            if imm not in (hi_a, hi_o):
                continue
            rt = (w >> 16) & 0x1F
            # search the next 12 instructions for the matching low half
            for j in range(i + 1, min(i + 13, n)):
                w2 = words[j]
                op2 = w2 >> 26
                rs2 = (w2 >> 21) & 0x1F
                imm2 = w2 & 0xFFFF
                if rs2 != rt:
                    continue
                if (op2 == 9 and imm == hi_a and imm2 == lo_a) or \
                   (op2 == 13 and imm == hi_o and imm2 == tva & 0xFFFF):
                    refs.append(vbase + i * 4)
                    break
    print("%-28r referenced from: %s"
          % (tname, ", ".join("0x%08X" % r for r in refs) if refs else "(no direct lui pair)"))
