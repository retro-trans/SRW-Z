"""VWF step 4: half the SHADOW pen advance for Latin codes.

Dialogue glyphs are drawn twice (main pen scratch 0x2c + shadow pen scratch
0x30). patch_font_advance only halves the MAIN advance (0x13AAE8); the shadow
pen advances separately at:

    0x13AB70  lh   a0, 0x30(at)     ; shadow pen X   (at = 0x70000000)
    0x13AB78  lh   v1, 0x38(at)     ; shadow advance amount (scratch 0x38)
    0x13AB7C  addu v1, a0, v1       ; shadow pen += advance
    0x13AB84  sh   v1, 0x30(at)

If only the main advance is halved, the two pens drift apart -> interleaved
"ghost" doubling that worsens along the line. This halves the SHADOW advance to
0x0C for the same Latin/digit/space codes so both pens track. Combined with
dest-width (12) + main advance (12), glyphs are tight, half-width, and clean.

Apply AFTER renderer + dest-width + advance. Hook lives in the setText cave.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
SH_SITE = 0x13AB78           # lh v1,0x38(at)
SH_SITE2 = 0x13AB7C          # addu v1,a0,v1
SETTEXT_CAVE = 0x188470
SH_AT = 0x188470 + 0x590     # free tail of cave (after squish/advance/vwf_flag)

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
    def lh(self, t, o, s): self._i(0x21, s, t, o)
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
    a = Asm(SH_AT)
    # in:  a0 = shadow pen X. out: v1 = a0 + advance (0x38 default, 0x0C Latin).
    # preserve t0-t3.
    a.addiu('sp', 'sp', -0x10)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.lui('at', 0x7000)
    a.lh('v1', 0x38, 'at')                 # default shadow advance
    a.lhu('t0', 0x60, 'at')                # glyph code
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')
    a.beqz('t2', 'chk_sp'); a.nop()
    a.li('v1', 0x0C)                       # letters/digits -> half
    a.jlbl('apply'); a.nop()
    a.label('chk_sp')
    a.ori('t3', 'zero', 0x8140)
    a.bne('t0', 't3', 'apply'); a.nop()
    a.li('v1', 0x0C)                       # space -> half
    a.label('apply')
    a.addu('v1', 'a0', 'v1')               # shadow pen + advance (replaces 0x13AB7C)
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x10)
    a.jr('ra'); a.lui('at', 0x7000)        # delay: restore at (0x13AB80 reloads it anyway)
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    a = build()
    code = a.bytes_()
    assert (SH_AT - SETTEXT_CAVE) + len(code) <= 0x660, "shadow hook overruns cave"

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(SH_AT, code)
    put(SH_SITE, struct.pack("<I", (3 << 26) | ((SH_AT >> 2) & 0x03FFFFFF)))   # lh->jal
    put(SH_SITE2, struct.pack("<I", 0))                                        # addu->nop
    open(dst, "wb").write(data)
    print("shadow-advance patch written:", dst)
    print("  sh hook @%#x len=%d" % (SH_AT, len(code)))
    print("  hooked %#x (lh->jal) + %#x (addu->nop)" % (SH_SITE, SH_SITE2))


if __name__ == "__main__":
    main()
