"""VWF step 3: half the sprite DEST-WIDTH for Latin/digit glyphs.

Resolves the ghosting wall in VWF.md. The per-glyph dest size is struct+0x10,
written in the blit 0x13A290 at:

    0x13AB48  lh  v1, 0x1c(s1)   ; s1 = font descriptor; +0x1c = cell size (0x18)
    0x13AB4C  sb  v1, 0x10(s0)   ; struct+0x10 = dest size (read back in flush 0x13ACA0)

For our Latin/digit codes we halve that value so the drawn sprite is 12px wide,
matching the 0x0C advance (patch_font_advance) and the left-12px squished art
(patch_font_squish) — so consecutive glyphs no longer overlap/ghost. Real kanji
(non-Latin codes) keep the full 0x18.

Layers on top of: patch_renderer -> patch_font_squish -> patch_font_advance.
Hook lives in the shared setText cave (0x188470, 0x660 bytes).

NOTE: needs a build + PCSX2 test pass. For fully tight glyphs the half-width
SOURCE sampling must also be active for these codes (native flag gp-0x7e8c=0x40,
see patch_font_flag.py / VWF.md); dest-width alone with a 24px source would
compress the full cell into 12px.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
DW_SITE = 0x13AB48           # lh v1,0x1c(s1)
DW_SITE2 = 0x13AB4C          # sb v1,0x10(s0)
SETTEXT_CAVE = 0x188470
DW_AT = 0x188470 + 0x500     # after setText+table+squish+advance, within the 0x660 cave

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
    def sra(self, d, t, sa): self._r('zero', t, d, sa, 3)
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
    def sb(self, t, o, s): self._i(0x28, s, t, o)
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
    a = Asm(DW_AT)
    # in:  s1 = font descriptor, s0 = struct ptr (both live in the blit loop).
    # do:  v1 = s1.cellsize; if code is Latin -> v1 >>= 1; struct.destsize = v1.
    # out: v1 clobbered (dead: reloaded at 0x13AB50); t0-t3 preserved.
    a.addiu('sp', 'sp', -0x10)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.lh('v1', 0x1c, 's1')                 # original cell size (0x18)
    a.lui('at', 0x7000)
    a.lhu('t0', 0x60, 'at')                # current glyph code
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')   # code < 0x824F?
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')   # code < 0x829B?
    a.beqz('t2', 'chk_sp'); a.nop()                          # >=0x829B -> not a letter
    a.sra('v1', 'v1', 1)                   # letters/digits -> half dest
    a.jlbl('store'); a.nop()
    a.label('chk_sp')
    a.ori('t3', 'zero', 0x8140)            # fullwidth space
    a.bne('t0', 't3', 'store'); a.nop()
    a.sra('v1', 'v1', 1)                   # space -> half dest
    a.label('store')
    a.sb('v1', 0x10, 's0')                 # struct+0x10 = (maybe halved) dest size
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x10)
    a.jr('ra'); a.nop()
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    a = build()
    code = a.bytes_()
    assert (DW_AT - SETTEXT_CAVE) + len(code) <= 0x660, "overflow setText cave"

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(DW_AT, code)
    # hook: lh v1,0x1c(s1) -> jal dw_hook ; sb v1,0x10(s0) -> nop (hook does the sb)
    put(DW_SITE, struct.pack("<I", (3 << 26) | ((DW_AT >> 2) & 0x03FFFFFF)))
    put(DW_SITE2, struct.pack("<I", 0))
    open(dst, "wb").write(data)
    print("dest-width patch written:", dst)
    print("  dw hook @%#x len=%d bytes" % (DW_AT, len(code)))
    print("  hooked %#x (lh->jal) + %#x (sb->nop)" % (DW_SITE, DW_SITE2))
    print("  NOTE: combine with the half-width source flag for fully tight glyphs (see VWF.md).")


if __name__ == "__main__":
    main()
