"""VWF step 2: half pen-advance for the (squished) Latin/digit glyphs.

The blit's per-glyph X advance is `addiu v0,v0,0x18` at 0x13AAE8 (pen X in GS
field 0x2c). This hooks it: for our Latin/digit codes (whose glyphs were
squished to half-width by patch_font_squish), advance by 0x0C instead of 0x18;
all other glyphs keep 0x18. Result: compact half-width English, Japanese
unchanged.

Codes half-advanced: 0x824F..0x829A (fullwidth digits/A-Z/a-z) and 0x8140
(space). These match the squished ranges. Apply AFTER patch_renderer +
patch_font_squish. Hook code lives in the setText cave's remaining space.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
ADV_SITE = 0x13AAE8          # addiu v0,v0,0x18  (per-glyph X advance)
ADV_SITE2 = 0x13AAEC         # lui at,0x7000     (its delay-safe successor)
SETTEXT_CAVE = 0x188470
ADV_AT = 0x188470 + 0x400    # after setText+table+squish, within the cave

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def addu(self, d, s, t): self._r(s, t, d, 0, 0x21)
    def sltu(self, d, s, t): self._r(s, t, d, 0, 0x2B)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lhu(self, t, o, s): self._i(0x25, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def li(self, t, i): self.addiu(t, 'zero', i)
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
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build():
    a = Asm(ADV_AT)
    # in: v0 = penX. out: v0 = penX + adv, at = 0x70000000. preserve t0-t3.
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.lui('at', 0x7000)
    a.lhu('t0', 0x60, 'at')          # glyph code (2-byte, zero-extended)
    a.li('t1', 0x18)                 # default full advance
    a.beqz('s3', 'apply'); a.nop()   # s3==0 => cache-build pass: keep full pitch
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')   # code < 0x824F?
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')   # code < 0x829B?
    a.beqz('t2', 'chk_sp'); a.nop()                          # >=0x829B -> not letter
    a.li('t1', 0x0C)                 # letters/digits -> half (match dest-width 0x0C)
    a.jlbl('apply'); a.nop()
    a.label('chk_sp')
    a.ori('t3', 'zero', 0x8140)
    a.bne('t0', 't3', 'apply'); a.nop()
    a.li('t1', 0x0C)                 # space -> half
    a.label('apply')
    a.addu('v0', 'v0', 't1')
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra')
    a.lui('at', 0x7000)              # delay slot: restore at for caller's sh v0,0x2c(at)
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    a = build()
    code = a.bytes_()
    assert (ADV_AT - SETTEXT_CAVE) + len(code) <= 0x660, "overflow setText cave"

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(ADV_AT, code)
    # hook the advance: addiu v0,v0,0x18 -> jal adv_hook ; lui at,0x7000 -> nop
    put(ADV_SITE, struct.pack("<I", (3 << 26) | ((ADV_AT >> 2) & 0x03FFFFFF)))
    put(ADV_SITE2, struct.pack("<I", 0))   # nop (adv_hook restores at)
    open(dst, "wb").write(data)
    print("advance patch written:", dst)
    print("  adv hook @%#x len=%d" % (ADV_AT, len(code)))
    print("  hooked %#x (addiu->jal) + %#x (lui->nop)" % (ADV_SITE, ADV_SITE2))


if __name__ == "__main__":
    main()
