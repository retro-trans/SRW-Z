"""Refine decompressor candidates: an LZ copy loop loads and stores through
the same base register (copying the output window onto itself). Rank by that.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile

path = sys.argv[1]
cands = [int(x, 16) for x in sys.argv[2:]]

f = open(path, "rb")
elf = ELFFile(f)
seg = [s for s in elf.iter_segments()
       if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
vbase, fbase = seg.header.p_vaddr, seg.header.p_offset
f.seek(fbase)
data = f.read(seg.header.p_filesz)

for va in cands:
    off = va - vbase
    n = 0x400 // 4
    words = struct.unpack("<%dI" % n, data[off:off + 0x400])
    lbu_bases, sb_bases = {}, {}
    sb_count = 0
    for w in words:
        op = w >> 26
        base = (w >> 21) & 0x1F
        if op == 36:
            lbu_bases[base] = lbu_bases.get(base, 0) + 1
        elif op == 40:
            sb_bases[base] = sb_bases.get(base, 0) + 1
            sb_count += 1
    shared = {b: min(lbu_bases[b], sb_bases[b])
              for b in lbu_bases if b in sb_bases}
    overlap = sum(shared.values())
    print("vaddr 0x%08X: sb=%2d  lbu-bases=%s sb-bases=%s  SHARED=%d %s"
          % (va, sb_count,
             sorted(lbu_bases.items()), sorted(sb_bases.items()),
             overlap, "  <<<" if overlap >= 2 else ""))
