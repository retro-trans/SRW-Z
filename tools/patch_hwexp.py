"""STAGE 2a: PT_LOAD the 1bpp half-width atlas, and at first setText expand it to
a 4bpp (PSMT4, 512-wide) image in free EE RAM at SCRATCH+0x70. NO upload/redirect
yet -> PINE-dump SCRATCH+0x70 and render to verify the expansion is correct.

setText is repointed to a trampoline (in the cave) that, once, zeroes the 8KB
4bpp region and expands each of 62 glyphs (idx 0-9,A-Z,a-z) into cell
(col*12, row*16), COLS=42, ink nibble 0xF; then jumps to the renderer cave
(0x188470) preserving a0-a3/ra. Apply on top of the fullwidth renderer ELF.
"""
import sys, struct

VBASE, FOFF = 0x100000, 0x1A80
CAVE = 0x188470
TRAMP = CAVE + 0x210          # after renderer code+table (ends ~0x20A)
ATLAS_VA = 0x01340000         # PT_LOAD target for the 1bpp atlas
SCRATCH = 0x01400000          # +0: flag ; +0x70: 8KB 4bpp image
IMG = SCRATCH + 0x70
COLS, CW, CH, VCELL = 42, 12, 12, 16
NGLYPH = 62
SETTEXT = 0x20C9B0
RENDERER_CAVE = 0x188470

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def here(self): return self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def addu(self, d, s, t): self._r(s, t, d, 0, 0x21)
    def subu(self, d, s, t): self._r(s, t, d, 0, 0x23)
    def and_(self, d, s, t): self._r(s, t, d, 0, 0x24)
    def or_(self, d, s, t): self._r(s, t, d, 0, 0x25)
    def slt(self, d, s, t): self._r(s, t, d, 0, 0x2A)
    def sltu(self, d, s, t): self._r(s, t, d, 0, 0x2B)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
    def srl(self, d, t, sa): self._r('zero', t, d, sa, 2)
    def sllv(self, d, t, s): self._r(s, t, d, 0, 4)
    def srlv(self, d, t, s): self._r(s, t, d, 0, 6)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lbu(self, t, o, s): self._i(0x24, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def sb(self, t, o, s): self._i(0x28, s, t, o)
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
    def beqz(self, s, l): self._b(4, s, 'zero', l)
    def bnez(self, s, l): self._b(5, s, 'zero', l)
    def j(self, a): self._e(lambda: (2 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build_tramp():
    a = Asm(TRAMP)
    # save s0-s5 (callee-saved) so we don't disturb setText's caller
    a.addiu('sp', 'sp', -0x20)
    for i, r in enumerate(['s0', 's1', 's2', 's3', 's4', 's5']):
        a.sw(r, i * 4, 'sp')
    a.la('s0', SCRATCH)
    a.lw('t0', 0, 's0')
    a.bnez('t0', 'done'); a.nop()
    a.li('t0', 1); a.sw('t0', 0, 's0')
    # zero 8KB at IMG
    a.la('s1', IMG)
    a.li('t1', 8192)
    a.label('zloop')
    a.sw('zero', 0, 's1'); a.addiu('s1', 's1', 4); a.addiu('t1', 't1', -4)
    a.bnez('t1', 'zloop'); a.nop()
    a.la('s1', IMG)                      # dest base
    a.la('s2', ATLAS_VA)                 # src base
    a.li('s3', 0)                        # idx
    a.label('eloop')
    # col/base_y from idx (2 rows)
    a.li('t0', COLS); a.slt('t1', 's3', 't0')
    a.bnez('t1', 'row0'); a.nop()
    a.addiu('t2', 's3', -COLS)           # col (row1)
    a.li('s4', VCELL)                    # base_y = 16
    a.jlbl('havecol'); a.nop()
    a.label('row0')
    a.ori('t2', 's3', 0)                 # col = idx (move)
    a.li('s4', 0)                        # base_y = 0
    a.label('havecol')
    # base_x = col*12  (t3)
    a.sll('t3', 't2', 3); a.sll('t4', 't2', 2); a.addu('t3', 't3', 't4')
    a.ori('s5', 't3', 0)                 # s5 = base_x
    # src glyph ptr = ATLAS_VA + idx*24  (t5)
    a.sll('t3', 's3', 4); a.sll('t4', 's3', 3); a.addu('t3', 't3', 't4')
    a.addu('t5', 's2', 't3')             # t5 = src glyph ptr
    a.li('t6', 0)                        # py
    a.label('pyloop')
    # row word = (src[py*2]<<8)|src[py*2+1]
    a.sll('t7', 't6', 1); a.addu('t7', 't5', 't7')
    a.lbu('t8', 0, 't7'); a.sll('t8', 't8', 8); a.lbu('t9', 1, 't7'); a.or_('t8', 't8', 't9')  # t8 = word
    # y = base_y + py ; yoff = y*256
    a.addu('t9', 's4', 't6')             # y
    a.sll('t9', 't9', 8)                 # yoff = y*256  (t9)
    a.li('t0', 0)                        # px
    a.label('pxloop')
    # bit = (word >> (15-px)) & 1
    a.li('t1', 15); a.subu('t1', 't1', 't0'); a.srlv('t2', 't8', 't1'); a.andi('t2', 't2', 1)
    a.beqz('t2', 'nextpx'); a.nop()
    # x = base_x + px ; off = yoff + (x>>1) ; nib=(x&1)*4
    a.addu('t3', 's5', 't0')             # x
    a.srl('t4', 't3', 1); a.addu('t4', 't9', 't4'); a.addu('t4', 's1', 't4')  # &dest byte
    a.andi('t7', 't3', 1); a.sll('t7', 't7', 2)   # nib shift (0 or 4)
    a.lbu('t1', 0, 't4')
    a.li('t2', 0xF); a.sllv('t2', 't2', 't7'); a.or_('t1', 't1', 't2')
    a.sb('t1', 0, 't4')
    a.label('nextpx')
    a.addiu('t0', 't0', 1); a.li('t1', CW); a.bne('t0', 't1', 'pxloop'); a.nop()
    a.addiu('t6', 't6', 1); a.li('t1', CH); a.bne('t6', 't1', 'pyloop'); a.nop()
    a.addiu('s3', 's3', 1); a.li('t1', NGLYPH); a.bne('s3', 't1', 'eloop'); a.nop()
    a.label('done')
    for i, r in enumerate(['s0', 's1', 's2', 's3', 's4', 's5']):
        a.lw(r, i * 4, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.j(RENDERER_CAVE); a.nop()
    return a


def add_ptload(data, blob, vaddr):
    e_phoff = struct.unpack('<I', data[28:32])[0]
    e_phnum = struct.unpack('<H', data[44:46])[0]
    e_phentsize = struct.unpack('<H', data[42:44])[0]
    while len(data) % 0x80:
        data.append(0)
    foff = len(data)
    assert (foff % 0x80) == (vaddr % 0x80), "PT_LOAD align"
    data += blob
    ph_new = e_phoff + e_phnum * e_phentsize
    assert ph_new + e_phentsize <= FOFF, "no PH room"
    data[ph_new:ph_new + e_phentsize] = struct.pack(
        '<8I', 1, foff, vaddr, vaddr, len(blob), len(blob), 7, 0x80)
    struct.pack_into('<H', data, 44, e_phnum + 1)
    return foff


def main():
    src, dst, atlas_bin = sys.argv[1], sys.argv[2], sys.argv[3]
    data = bytearray(open(src, "rb").read())
    atlas = open(atlas_bin, "rb").read()
    assert len(atlas) == NGLYPH * 24, len(atlas)

    tr = build_tramp()

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(TRAMP, tr.bytes_())
    assert (TRAMP - CAVE) + len(tr.bytes_()) <= 0x660, "tramp overruns cave (%#x)" % ((TRAMP - CAVE) + len(tr.bytes_()))
    # repoint setText -> tramp
    put(SETTEXT, struct.pack("<I", (2 << 26) | ((TRAMP >> 2) & 0x03FFFFFF)))
    foff = add_ptload(data, atlas, ATLAS_VA)
    newsz = len(data)
    assert newsz <= 0x350000, "ELF grew past sector limit (%#x)!" % newsz
    open(dst, "wb").write(data)
    print("hwexp written:", dst)
    print("  tramp @%#x (%dB), atlas PT_LOAD @%#x foff %#x (%dB), ELF=%#x" %
          (TRAMP, len(tr.bytes_()), ATLAS_VA, foff, len(atlas), newsz))


if __name__ == "__main__":
    main()
