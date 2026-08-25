"""Word-by-word MIPS disassembler for PS2 EE code.

Capstone chokes on EE-specific ops (sq/lq/mmi), which aborts linear sweeps.
Decode each 4-byte word independently and print raw words it cannot decode,
with a manual decode for the common EE loads/stores.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN

REG = ("zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
       "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra").split()

path = sys.argv[1]
target = int(sys.argv[2], 16)
span = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x300

f = open(path, "rb")
elf = ELFFile(f)
seg = [s for s in elf.iter_segments()
       if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
f.seek(seg.header.p_offset + (target - seg.header.p_vaddr))
code = f.read(span)

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)


def ee_decode(w):
    op = w >> 26
    base, rt = (w >> 21) & 0x1F, (w >> 16) & 0x1F
    imm = w & 0xFFFF
    if imm >= 0x8000:
        imm -= 0x10000
    if op == 0x1F:
        return "sq       $%s, %#x($%s)" % (REG[rt], imm, REG[base])
    if op == 0x1E:
        return "lq       $%s, %#x($%s)" % (REG[rt], imm, REG[base])
    return None


for i in range(0, len(code) - 3, 4):
    w = struct.unpack("<I", code[i:i + 4])[0]
    addr = target + i
    txt = None
    for ins in md.disasm(code[i:i + 4], addr):
        txt = "%-8s %s" % (ins.mnemonic, ins.op_str)
        break
    if txt is None:
        txt = ee_decode(w) or (".word    0x%08X" % w)
    print("  %08X  %s" % (addr, txt))
