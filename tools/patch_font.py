"""VWF step 1: swap fullwidth Latin/digit glyphs for half-width ones (multi-cave).

Boot-hook (at font-init tail 0x13A23C = `jal 0x139f00`) expands 24x24 1bpp
half-width glyphs into the decoded font buffer (desc 0x46E3A8 -> 0x9AE610) at
each glyph's JIS index, overwriting the fullwidth glyph. setText already emits
these codes, so no addressing change.

The ELF has no single safe cave big enough for the ~4.7 KB glyph blob, so the
data is split across several verified-dead caves (no jal/ptr/computed/branch
refs into them). The hook reads a chunk table {addr,count} and processes each.

Verified-safe caves (see docs/VWF.md; 0x188470 is used by the setText patch):
  code+table: 0x3B9400 (1472)
  data:       0x376580 (1232), 0x23C370 (1024), 0x3B99C0 (960),
              0x3EE640 (928), 0x1A6460 (896)
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
HOOK_SITE = 0x13A23C
DISPLACED = 0x139F00
FONTBUF_LUI = 0x47
FONTBUF_OFF = -0x1C58

CODE_CAVE = (0x3B9400, 1472)
DATA_CAVES = [(0x376580, 1232), (0x23C370, 1024), (0x3B99C0, 960),
              (0x3EE640, 928), (0x1A6460, 896)]
REC = 76  # u16 idx, u8 w, u8 pad, 72 glyph

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def addu(self, d, s, t): self._r(s, t, d, 0, 0x21)
    def subu(self, d, s, t): self._r(s, t, d, 0, 0x23)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
    def srl(self, d, t, sa): self._r('zero', t, d, sa, 2)
    def srlv(self, d, t, s): self._r(s, t, d, 0, 6)
    def _or(self, d, s, t): self._r(s, t, d, 0, 0x25)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def move(self, d, s): self.addu(d, s, 'zero')
    def nop(self): self.sll('zero', 'zero', 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
    def slti(self, t, s, i): self._i(0x0A, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lbu(self, t, o, s): self._i(0x24, s, t, o)
    def lhu(self, t, o, s): self._i(0x25, s, t, o)
    def sb(self, t, o, s): self._i(0x28, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def li(self, t, i): self.addiu(t, 'zero', i)
    def la(self, t, a): self.lui(t, (a >> 16) & 0xFFFF); self.ori(t, t, a & 0xFFFF)
    def _b(self, op, rs, rt, lbl):
        idx = len(self.ins)
        def f(_i=idx, _op=op, _rs=rs, _rt=rt, _l=lbl):
            off = (self.labels[_l] - (self.base + _i * 4 + 4)) >> 2
            return (_op << 26) | (R[_rs] << 21) | (R[_rt] << 16) | (off & 0xFFFF)
        self._e(f)
    def beq(self, s, t, l): self._b(4, s, t, l)
    def bne(self, s, t, l): self._b(5, s, t, l)
    def beqz(self, s, l): self.beq(s, 'zero', l)
    def bnez(self, s, l): self.bne(s, 'zero', l)
    def jal(self, a): self._e(lambda: (3 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build_hook(table_addr):
    a = Asm(CODE_CAVE[0])
    a.addiu('sp', 'sp', -0x40)
    for k, r in enumerate(['ra', 's0', 's1', 's2', 's3', 's4', 's5', 's6']):
        a.sw(r, 0x3C - k * 4, 'sp')
    a.jal(DISPLACED); a.nop()
    a.lui('at', FONTBUF_LUI); a.lw('s0', FONTBUF_OFF, 'at')
    a.beqz('s0', 'done'); a.nop()
    a.la('s5', table_addr)
    a.lhu('s6', 0, 's5')           # nchunks
    a.addiu('s5', 's5', 2)
    a.label('chunk')
    a.beqz('s6', 'done'); a.nop()
    a.lw('s1', 0, 's5')            # record ptr
    a.lhu('s2', 4, 's5')          # nrec
    a.addiu('s5', 's5', 6)
    a.label('rec')
    a.beqz('s2', 'chunk_next'); a.nop()
    a.lhu('t0', 0, 's1')          # idx
    a.addiu('s3', 's1', 4)       # glyph ptr
    a.sll('t1', 't0', 8); a.sll('t2', 't0', 5); a.addu('t1', 't1', 't2')
    a.addu('s4', 's0', 't1')      # dest = fontbuf + idx*288
    a.li('t0', 0)                 # y
    a.label('yl')
    a.li('t1', 0)                 # x
    a.label('xl')
    a.sll('t2', 't0', 1); a.addu('t2', 't2', 't0')  # y*3
    a.srl('t3', 't1', 3); a.addu('t2', 't2', 't3')
    a.addu('t2', 's3', 't2'); a.lbu('t2', 0, 't2')  # src byte
    a.andi('t3', 't1', 7); a.li('t4', 7); a.subu('t3', 't4', 't3')
    a.srlv('t2', 't2', 't3'); a.andi('t2', 't2', 1)
    a.li('t9', 0); a.beqz('t2', 'z'); a.nop(); a.li('t9', 0xF)
    a.label('z')
    a.sll('t3', 't0', 3); a.sll('t4', 't0', 2); a.addu('t3', 't3', 't4')  # y*12
    a.srl('t4', 't1', 1); a.addu('t3', 't3', 't4')
    a.addu('t3', 's4', 't3'); a.lbu('t4', 0, 't3')
    a.andi('t5', 't1', 1); a.bnez('t5', 'hi'); a.nop()
    a.andi('t4', 't4', 0xF0); a._or('t4', 't4', 't9'); a.jlbl('stb'); a.nop()
    a.label('hi')
    a.andi('t4', 't4', 0x0F); a.sll('t9', 't9', 4); a._or('t4', 't4', 't9')
    a.label('stb')
    a.sb('t4', 0, 't3')
    a.addiu('t1', 't1', 1); a.slti('at', 't1', 24); a.bnez('at', 'xl'); a.nop()
    a.addiu('t0', 't0', 1); a.slti('at', 't0', 24); a.bnez('at', 'yl'); a.nop()
    a.addiu('s1', 's1', REC); a.addiu('s2', 's2', -1); a.jlbl('rec'); a.nop()
    a.label('chunk_next')
    a.addiu('s6', 's6', -1); a.jlbl('chunk'); a.nop()
    a.label('done')
    for k, r in enumerate(['ra', 's0', 's1', 's2', 's3', 's4', 's5', 's6']):
        a.lw(r, 0x3C - k * 4, 'sp')
    a.jr('ra'); a.addiu('sp', 'sp', 0x40)
    return a


def main():
    src, dst, blobf = sys.argv[1], sys.argv[2], sys.argv[3]
    data = bytearray(open(src, "rb").read())
    blob = open(blobf, "rb").read()
    count = struct.unpack_from("<H", blob, 0)[0]
    records = [blob[2 + i * REC: 2 + (i + 1) * REC] for i in range(count)]
    assert all(len(r) == REC for r in records)

    code_len = len(build_hook(0).bytes_())
    table_addr = CODE_CAVE[0] + code_len
    # capacity of the code cave for records after code+table (reserve 2+8*6=50 for table)
    TABLE_RESERVE = 2 + 8 * 6
    caves = [(CODE_CAVE[0], table_addr + TABLE_RESERVE, CODE_CAVE[0] + CODE_CAVE[1])] + \
            [(a, a, a + s) for a, s in DATA_CAVES]
    # greedily pack records into caves; produce chunks (data_addr, [records])
    chunks = []  # (start_addr, recs)
    ri = 0
    for base, dstart, dend in caves:
        cap = (dend - dstart) // REC
        if cap <= 0 or ri >= len(records):
            continue
        take = min(cap, len(records) - ri)
        chunks.append((dstart, records[ri:ri + take]))
        ri += take
    assert ri == len(records), "not enough cave space: placed %d/%d" % (ri, len(records))
    assert len(chunks) <= 8

    # build chunk table
    table = struct.pack("<H", len(chunks))
    for addr, recs in chunks:
        table += struct.pack("<IH", addr, len(recs))
    assert len(table) <= TABLE_RESERVE

    a = build_hook(table_addr)
    code = a.bytes_()
    assert len(code) == code_len

    def put(vaddr, b):
        o = FOFF + (vaddr - VBASE); data[o:o + len(b)] = b
    put(CODE_CAVE[0], code)
    put(table_addr, table)
    for addr, recs in chunks:
        put(addr, b"".join(recs))
    put(HOOK_SITE, struct.pack("<I", (3 << 26) | ((CODE_CAVE[0] >> 2) & 0x03FFFFFF)))

    open(dst, "wb").write(data)
    print("multi-cave font-swap written:", dst)
    print("  code %#x len=%d  table@%#x (%d B, %d chunks)" % (CODE_CAVE[0], code_len, table_addr, len(table), len(chunks)))
    for addr, recs in chunks:
        print("    chunk @%#x  %d records (%d B)" % (addr, len(recs), len(recs) * REC))
    print("  hook %#x -> jal %#x" % (HOOK_SITE, CODE_CAVE[0]))


if __name__ == "__main__":
    main()
