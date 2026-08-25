"""VWF (reliable, code-only): condense fullwidth Latin glyphs to half-width.

No glyph data to store, so the hook lives in the spare space of the PROVEN-safe
setText cave (0x188470; setText code is ~332 B, leaving ~1.3 KB). It hooks the
font-init tail (0x13A23C = `jal 0x139f00`) and, for the Latin/digit glyph index
ranges in the decoded font buffer (0x9AE610), horizontally squishes each 24x24
4bpp glyph 2:1 into its left 12 px (max of each column pair), clearing the right
half. Combined with a later advance patch this gives compact proportional text;
on its own it makes the glyphs half-width.

Apply AFTER patch_renderer.py (setText). Uses only the setText cave -> reliable.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
HOOK_SITE = 0x13A23C
DISPLACED = 0x139F00
SETTEXT_CAVE = 0x188470
SQUISH_AT = 0x188470 + 0x220   # after setText code (332B) + fullwidth table (190B), in-cave
FONTBUF_LUI = 0x47
FONTBUF_OFF = -0x1C58

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
    def _or(self, d, s, t): self._r(s, t, d, 0, 0x25)
    def _and(self, d, s, t): self._r(s, t, d, 0, 0x24)
    def slt(self, d, s, t): self._r(s, t, d, 0, 0x2A)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def move(self, d, s): self.addu(d, s, 'zero')
    def nop(self): self.sll('zero', 'zero', 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
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
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
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


# glyph index ranges to squish (confirmed from decoded buffer): [start,end)
RANGES = [(207, 217), (224, 250), (257, 283)]


def build(ranges_addr):
    a = Asm(SQUISH_AT)
    a.addiu('sp', 'sp', -0x30)
    for k, r in enumerate(['ra', 's0', 's1', 's2', 's3', 's4', 's5', 's6']):
        a.sw(r, 0x2C - k * 4, 'sp')
    a.jal(DISPLACED); a.nop()
    a.lui('at', FONTBUF_LUI); a.lw('s0', FONTBUF_OFF, 'at')
    a.beqz('s0', 'done'); a.nop()
    a.la('s5', ranges_addr); a.li('s6', len(RANGES))
    a.label('rng')
    a.beqz('s6', 'done'); a.nop()
    a.lhu('s3', 0, 's5')          # start idx (u16, up to ~283)
    a.lhu('s4', 2, 's5')          # end idx
    a.addiu('s5', 's5', 4)
    a.label('idx')
    a.slt('at', 's3', 's4'); a.beqz('at', 'rng_next'); a.nop()
    # cell base = s0 + idx*288
    a.sll('t8', 's3', 8); a.sll('t9', 's3', 5); a.addu('t8', 't8', 't9')
    a.addu('s1', 's0', 't8')      # s1 = cell base
    a.li('t0', 0)                 # y
    a.label('yl')
    a.sll('t1', 't0', 3); a.sll('t2', 't0', 2); a.addu('t1', 't1', 't2')  # y*12
    a.addu('s2', 's1', 't1')      # s2 = row base (12 bytes = 24 nibbles)
    a.li('t3', 0)                 # x (0..11 dest)
    a.label('xl')
    # read src nibbles 2x, 2x+1 ; compute max -> v (t7)
    a.sll('t4', 't3', 1)          # 2x
    # nib(col): byte s2+col>>1 ; if col&1 hi else lo
    # a = nib(2x): 2x is even -> low nibble of byte s2+x
    a.lbu('t5', 0, 's2')          # placeholder; recompute properly below
    # --- nibble 2x (even) ---
    a.addu('t6', 's2', 't3')      # s2 + x  (since (2x)>>1 = x)
    a.lbu('t5', 0, 't6'); a.andi('t5', 't5', 0x0F)   # a = low nibble
    # --- nibble 2x+1 (odd) -> high nibble of same byte (s2+x) ---
    a.lbu('t7', 0, 't6'); a.srl('t7', 't7', 4)       # b = high nibble
    # v = max(a,b)
    a.slt('at', 't5', 't7'); a.beqz('at', 'nomax'); a.nop(); a.move('t5', 't7')
    a.label('nomax')             # t5 = v (max)
    # write v into dest nibble x: byte s2 + x>>1 ; if x&1 hi else lo
    a.srl('t6', 't3', 1); a.addu('t6', 's2', 't6')   # dest byte ptr
    a.lbu('t7', 0, 't6')
    a.andi('at', 't3', 1); a.bnez('at', 'wodd'); a.nop()
    a.andi('t7', 't7', 0xF0); a._or('t7', 't7', 't5'); a.jlbl('wst'); a.nop()
    a.label('wodd')
    a.sll('t5', 't5', 4); a.andi('t7', 't7', 0x0F); a._or('t7', 't7', 't5')
    a.label('wst')
    a.sb('t7', 0, 't6')
    a.addiu('t3', 't3', 1); a.slti('at', 't3', 12); a.bnez('at', 'xl'); a.nop()
    # clear right half: dest bytes for cols 12..23 -> bytes s2+6 .. s2+11
    a.li('t3', 6)
    a.label('cl')
    a.addu('t6', 's2', 't3'); a.sb('zero', 0, 't6')
    a.addiu('t3', 't3', 1); a.slti('at', 't3', 12); a.bnez('at', 'cl'); a.nop()
    a.addiu('t0', 't0', 1); a.slti('at', 't0', 24); a.bnez('at', 'yl'); a.nop()
    a.addiu('s3', 's3', 1); a.jlbl('idx'); a.nop()
    a.label('rng_next')
    a.addiu('s6', 's6', -1); a.jlbl('rng'); a.nop()
    a.label('done')
    for k, r in enumerate(['ra', 's0', 's1', 's2', 's3', 's4', 's5', 's6']):
        a.lw(r, 0x2C - k * 4, 'sp')
    a.jr('ra'); a.addiu('sp', 'sp', 0x30)
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    code_len = len(build(0).bytes_())
    ranges_addr = SQUISH_AT + code_len
    a = build(ranges_addr)
    code = a.bytes_()
    rtab = b"".join(struct.pack("<HH", s, e) for s, e in RANGES)
    # ensure we stay within the setText cave (0x188470 + 0x660)
    assert (SQUISH_AT - SETTEXT_CAVE) + len(code) + len(rtab) <= 0x660, "overflow setText cave"

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(SQUISH_AT, code)
    put(ranges_addr, rtab)
    put(HOOK_SITE, struct.pack("<I", (3 << 26) | ((SQUISH_AT >> 2) & 0x03FFFFFF)))
    open(dst, "wb").write(data)
    print("squish patch written:", dst)
    print("  squish hook @%#x  len=%d  ranges@%#x" % (SQUISH_AT, code_len, ranges_addr))
    print("  hook %#x -> jal %#x" % (HOOK_SITE, SQUISH_AT))
    print("  cave use: %d / 0x660" % ((SQUISH_AT - SETTEXT_CAVE) + len(code) + len(rtab)))


if __name__ == "__main__":
    main()
