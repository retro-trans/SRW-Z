"""Standard-VWF helper: per-Latin flag + disable the outline for Latin.

Unlike patch_vwf1 this does NOT shrink the sprite (that was non-standard and
caused the tight-pitch satellites). It only:
  - sets struct+0x1d = 1 for Latin codes (free byte), and
  - forces struct+0x1c = 0 for Latin (disable the 8-sprite outline).

Use with the STANDARD VWF recipe: patch_renderer -> patch_font_squish (art
left-aligned in the left 12px, right half transparent) -> this -> advance(0x0C).
The full 24px sprite still draws, but its right half is transparent, so a tight
0x0C advance overlaps only transparent pixels = clean, and no outline copies to
smear into neighbors.

Hook lives in the setText cave 0x188470 (after renderer code+table).
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
CAVE = 0x188470
BHOOK = CAVE + 0x500         # after renderer(~0x20A) + squish(~0x220..) + advance(0x400)
B_S1 = 0x13AB68             # lb v1,0x50(s1)
B_S2 = 0x13AB6C             # sb v1,0x1c(s0)

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def sltu(self, d, s, t): self._r(s, t, d, 0, 0x2B)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lhu(self, t, o, s): self._i(0x25, s, t, o)
    def lb(self, t, o, s): self._i(0x20, s, t, o)
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


def build_bhook():
    a = Asm(BHOOK)
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t2', 4, 'sp'); a.sw('t3', 8, 'sp'); a.sw('t4', 0xC, 'sp')
    a.lb('t4', 0x50, 's1')          # original outline flag
    # v1 = is-latin(code)
    a.lui('at', 0x7000)
    a.lhu('t0', 0x60, 'at')
    a.li('v1', 0)
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')
    a.beqz('t2', 'chk_sp'); a.nop()
    a.li('v1', 1); a.jlbl('flag_done'); a.nop()
    a.label('chk_sp')
    a.ori('t3', 'zero', 0x8140)
    a.bne('t0', 't3', 'flag_done'); a.nop()
    a.li('v1', 1)
    a.label('flag_done')
    a.sb('v1', 0x1d, 's0')          # struct+0x1d = latin flag
    a.beqz('v1', 'keep_outline'); a.nop()
    a.li('t4', 0)                   # latin -> outline off
    a.label('keep_outline')
    a.sb('t4', 0x1c, 's0')          # struct+0x1c (0 for latin)
    a.lw('t0', 0, 'sp'); a.lw('t2', 4, 'sp'); a.lw('t3', 8, 'sp'); a.lw('t4', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.nop()
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    bh = build_bhook(); code = bh.bytes_()
    assert (BHOOK - CAVE) + len(code) <= 0x660, "cave overflow"

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(BHOOK, code)
    put(B_S1, struct.pack("<I", (3 << 26) | ((BHOOK >> 2) & 0x03FFFFFF)))  # jal
    put(B_S2, struct.pack("<I", 0))                                        # nop
    open(dst, "wb").write(data)
    print("VWF flag+outline-off written:", dst, "(bhook @%#x, %d B)" % (BHOOK, len(code)))


if __name__ == "__main__":
    main()
