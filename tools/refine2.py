"""Which SJIS-decode cluster also handles '$' (0x24) and '\\n' (0x0A)?
Only the dialogue printer needs both."""
import sys
import struct
from elftools.elf.elffile import ELFFile

path = sys.argv[1]
cands = [int(x, 16) for x in sys.argv[2:]]
f = open(path, "rb")
elf = ELFFile(f)
seg = [s for s in elf.iter_segments()
       if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
vbase = seg.header.p_vaddr
f.seek(seg.header.p_offset)
data = f.read(seg.header.p_filesz)

for va in cands:
    off = va - vbase - 0x400          # look wide around the cluster
    span = 0x1000
    words = struct.unpack("<%dI" % (span // 4), data[off:off + span])
    dollar = nl = 0
    for w in words:
        op = w >> 26
        imm = w & 0xFFFF
        rs = (w >> 21) & 0x1F
        # li reg,0x24 / cmp-imm 0x24 / xori 0x24
        if op in (8, 9, 10, 11, 12, 13, 14) and imm == 0x24:
            dollar += 1
        if op in (8, 9, 10, 11, 12, 13, 14) and imm == 0x0A:
            nl += 1
    print("0x%08X  '$'-imm: %2d   0x0A-imm: %2d %s"
          % (va, dollar, nl, "   <<<" if dollar and nl else ""))
