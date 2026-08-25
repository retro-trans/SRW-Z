import sys, capstone
VBASE=0x100000; FOFF=0x1A80
elf=open(r'E:\Projects\SRW Z\_work\optx\en_elf\SLPS_258.87','rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64+capstone.CS_MODE_LITTLE_ENDIAN)
start=int(sys.argv[1],16); end=int(sys.argv[2],16)
off=FOFF+(start-VBASE)
code=elf[off:off+(end-start)]
addr=start
while addr < end:
    o=FOFF+(addr-VBASE)
    ins=list(md.disasm(elf[o:o+4], addr))
    if ins:
        print('0x%06X: %-10s %s' % (addr, ins[0].mnemonic, ins[0].op_str))
    else:
        w=int.from_bytes(elf[o:o+4],'little')
        print('0x%06X: .word      0x%08X' % (addr, w))
    addr+=4
