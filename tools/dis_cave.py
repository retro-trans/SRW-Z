# -*- coding: utf-8 -*-
"""Minimal MIPS-I disassembler for the font caves. dis_cave.py <iso> <va> [n]"""
import struct, sys
R="zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split()
def foff(va): return 0x34D770+(va-0x78A070) if va>=0x78A070 else va-0x100000+0x1A80
def sx(i): return i-0x10000 if i&0x8000 else i
SPEC={0x00:"sll",0x02:"srl",0x03:"sra",0x04:"sllv",0x06:"srlv",0x07:"srav",0x08:"jr",
      0x09:"jalr",0x0A:"movz",0x0B:"movn",0x10:"mfhi",0x12:"mflo",0x18:"mult",
      0x19:"multu",0x1A:"div",0x21:"addu",0x23:"subu",0x24:"and",0x25:"or",
      0x26:"xor",0x27:"nor",0x2A:"slt",0x2B:"sltu"}
OPS={0x04:"beq",0x05:"bne",0x06:"blez",0x07:"bgtz",0x08:"addi",0x09:"addiu",
     0x0A:"slti",0x0B:"sltiu",0x0C:"andi",0x0D:"ori",0x0E:"xori",0x0F:"lui",
     0x20:"lb",0x21:"lh",0x23:"lw",0x24:"lbu",0x25:"lhu",0x28:"sb",0x29:"sh",0x2B:"sw"}
def dis(x,va):
    op=x>>26; rs=(x>>21)&31; rt=(x>>16)&31; rd=(x>>11)&31; sa=(x>>6)&31
    im=x&0xFFFF; fn=x&0x3F
    if x==0: return "nop"
    if op==0:
        m=SPEC.get(fn)
        if not m: return ".word %08X"%x
        if m in ("jr","jalr"): return "%s %s"%(m,R[rs])
        if m in ("mfhi","mflo"): return "%s %s"%(m,R[rd])
        if m in ("mult","multu","div"): return "%s %s,%s"%(m,R[rs],R[rt])
        if m in ("sll","srl","sra"): return "%s %s,%s,%d"%(m,R[rd],R[rt],sa)
        return "%s %s,%s,%s"%(m,R[rd],R[rs],R[rt])
    if op in (0x02,0x03): return "%s %#x"%("j" if op==2 else "jal",(x&0x3FFFFFF)<<2)
    m=OPS.get(op)
    if not m: return ".word %08X"%x
    if m=="lui": return "lui %s,%#x"%(R[rt],im)
    if m in ("beq","bne"): return "%s %s,%s,%#x"%(m,R[rs],R[rt],va+4+sx(im)*4)
    if m in ("blez","bgtz"): return "%s %s,%#x"%(m,R[rs],va+4+sx(im)*4)
    if m in ("lb","lh","lw","lbu","lhu","sb","sh","sw"):
        return "%s %s,%d(%s)"%(m,R[rt],sx(im),R[rs])
    return "%s %s,%s,%#x"%(m,R[rt],R[rs],im)
def main():
    iso=sys.argv[1]; va=int(sys.argv[2],0); n=int(sys.argv[3]) if len(sys.argv)>3 else 40
    f=open(iso,"rb"); f.seek(455*2048); elf=f.read(3471624); f.close()
    for i in range(n):
        a=va+i*4; x=struct.unpack_from("<I",elf,foff(a))[0]
        print("  %#08x  %08X  %s"%(a,x,dis(x,a)))
main()
