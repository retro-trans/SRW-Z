"""Test whether two PS2 SRW ELFs share text middleware by searching for the
first ELF's SJIS-classifier byte pattern inside the second, and reporting how
much code is byte-identical overall.
"""
import sys
import struct
from elftools.elf.elffile import ELFFile


def load(path):
    f = open(path, "rb")
    elf = ELFFile(f)
    seg = [s for s in elf.iter_segments()
           if s.header.p_type == "PT_LOAD" and s.header.p_filesz > 0][0]
    f.seek(seg.header.p_offset)
    return seg.header.p_vaddr, f.read(seg.header.p_filesz)


srwz_path, other_path = sys.argv[1], sys.argv[2]
zbase, z = load(srwz_path)
obase, o = load(other_path)
print("SRW Z: vaddr 0x%X, %d bytes" % (zbase, len(z)))
print("other: vaddr 0x%X, %d bytes" % (obase, len(o)))

# 1) search for SRW Z's SJIS classifier region (0x2010D8..0x201120) in `other`
cstart = 0x2010D8 - zbase
needle = z[cstart:cstart + 0x48]
pos = o.find(needle)
print("\nSRW Z SJIS-classifier 0x48-byte pattern in other: %s"
      % (("FOUND at file 0x%X (vaddr 0x%X)" % (pos, obase + pos)) if pos >= 0 else "not found"))

# try a shorter core (the four slti lead checks)
core = z[0x2010DC - zbase:0x201100 - zbase]
pos2 = o.find(core)
print("shorter classifier core (%d bytes) in other: %s"
      % (len(core), ("FOUND at vaddr 0x%X" % (obase + pos2)) if pos2 >= 0 else "not found"))

# 2) overall shared-code estimate: sample 4KB-aligned chunks of SRW Z, see how
# many appear verbatim in `other`
CH = 256
hits = total = 0
for i in range(0, len(z) - CH, 4096):
    total += 1
    chunk = z[i:i + CH]
    if chunk.count(0) > CH * 0.6:
        continue
    if o.find(chunk) >= 0:
        hits += 1
print("\nshared 256B chunks (sampled every 4KB): %d / %d = %.1f%%"
      % (hits, total, 100.0 * hits / max(1, total)))
