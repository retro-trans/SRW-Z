"""Compare structural markers of the text renderer between two PS2 ELFs, to see
whether both use SRW Z's two-pen + 8-sprite-outline scheme.

Markers:
  - lui $at,0x7000  (scratchpad 0x70000000 pen state -- SRW Z's blit hammers this)
  - addiu r,r,+/-0x10 and +/-8  (the outline offset adjustments; SRW Z has dozens
    clustered in the flush)
  - sll r,r,8 followed near by 'or' (2-byte SJIS code assembly)
"""
import sys, struct
from elftools.elf.elffile import ELFFile


def load(p):
    f = open(p, "rb"); e = ELFFile(f)
    s = [x for x in e.iter_segments() if x.header.p_type == "PT_LOAD" and x.header.p_filesz][0]
    f.seek(s.header.p_offset)
    return s.header.p_vaddr, f.read(s.header.p_filesz)


def scan(path):
    vb, d = load(path)
    n = len(d) // 4
    w = struct.unpack("<%dI" % n, d[:n * 4])
    lui7000 = 0
    off10 = off8 = 0
    off10_runs = []           # clusters of >=6 outline offsets within 64 instrs
    window = []
    for i, x in enumerate(w):
        op = x >> 26
        rs = (x >> 21) & 0x1F
        rt = (x >> 16) & 0x1F
        imm = x & 0xFFFF
        if op == 0x0F and rt == 1 and imm == 0x7000:      # lui $at,0x7000
            lui7000 += 1
        if op == 0x09 and rs == rt:                        # addiu r,r,imm
            s = imm - 0x10000 if imm >= 0x8000 else imm
            if s in (0x10, -0x10):
                off10 += 1
            elif s in (8, -8):
                off8 += 1
    return {"size": len(d), "lui7000": lui7000, "off10(+-0x10)": off10, "off8(+-8)": off8}


for p in sys.argv[1:]:
    r = scan(p)
    print("%-40s %s" % (p.split("\\")[-1], r))
