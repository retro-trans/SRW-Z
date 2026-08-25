"""REDIRECT PROOF (no atlas): set a per-Latin flag in the blit, then in the flush
override the just-built TEX0's TBP0 -> 0 for Latin glyphs only. If Latin text
garbles (samples VRAM 0) while Japanese stays clean, the per-glyph TBP0 override
mechanism works -> the real atlas redirect is viable. Apply on top of the
fullwidth renderer ELF (patch_renderer).

Hooks:
  blit 0x13AB68/6C -> bhook: struct+0x13 = Latin flag (code 0x824f..0x829a,0x8140)
  flush 0x13B278 (lw t0,0x14(a3)) -> j FLHOOK. Its delay slot 0x13B27C
    (addiu a0,a0,8) still runs, so in FLHOOK [a0-8] = the stored TEX0 qword.
    FLHOOK: if Latin, zero TBP0 (bits0-13) of [a0-8]; then do the displaced
    lw t0,0x14(a3); j 0x13B280.
"""
import sys, struct

VBASE, FOFF, CAVE = 0x100000, 0x1A80, 0x188470
BHOOK = CAVE + 0x220
FLHOOK = CAVE + 0x440
B_S1, B_S2 = 0x13AB68, 0x13AB6C
FL_SITE = 0x13B278            # lw t0,0x14(a3)  (delay 0x13B27C addiu a0,a0,8)
FL_RET = 0x13B280

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def sltu(self, d, s, t): self._r(s, t, d, 0, 0x2B)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
    def srl(self, d, t, sa): self._r('zero', t, d, sa, 2)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
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
    def beqz(self, s, l): self._b(4, s, 'zero', l)
    def bnez(self, s, l): self._b(5, s, 'zero', l)
    def beq(self, s, t, l): self._b(4, s, t, l)
    def bne(self, s, t, l): self._b(5, s, t, l)
    def j(self, a): self._e(lambda: (2 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def is_latin(a):
    """v1 = 1 if scratch-0x60 code is fullwidth Latin/space else 0. clobbers t0,t2,t3,at."""
    a.lui('at', 0x7000); a.lhu('t0', 0x60, 'at'); a.li('v1', 0)
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')
    a.beqz('t2', 'chk_sp'); a.nop()
    a.li('v1', 1); a.jlbl('flag_done'); a.nop()
    a.label('chk_sp'); a.ori('t3', 'zero', 0x8140)
    a.bne('t0', 't3', 'flag_done'); a.nop()
    a.li('v1', 1)
    a.label('flag_done')


def build_bhook():
    a = Asm(BHOOK)
    a.lb('v1', 0x50, 's1'); a.sb('v1', 0x1c, 's0')     # original outline-flag copy
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t2', 4, 'sp'); a.sw('t3', 8, 'sp'); a.sw('v1', 0xC, 'sp'); a.sw('at', 0x10, 'sp')
    is_latin(a)
    a.sb('v1', 0x13, 's0')                              # struct+0x13 = Latin flag
    a.lw('t0', 0, 'sp'); a.lw('t2', 4, 'sp'); a.lw('t3', 8, 'sp'); a.lw('v1', 0xC, 'sp'); a.lw('at', 0x10, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.nop()
    return a


def build_flhook():
    a = Asm(FLHOOK)
    # a0 already advanced +8 by the delay slot; [a0-8] = stored TEX0 qword.
    a.sw('t8', -8, 'sp')
    a.lb('t8', 0x13, 'a3')                 # Latin flag
    a.beqz('t8', 'fl_restore'); a.nop()
    a.lw('t8', -8, 'a0')                   # low32 of TEX0 (TBP0 = bits 0-13)
    a.srl('t8', 't8', 14); a.sll('t8', 't8', 14)   # TBP0 -> 0
    a.sw('t8', -8, 'a0')
    a.label('fl_restore')
    a.lw('t8', -8, 'sp')
    a.lw('t0', 0x14, 'a3')                 # displaced original
    a.j(FL_RET); a.nop()
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    bh = build_bhook(); put(BHOOK, bh.bytes_())
    fh = build_flhook(); put(FLHOOK, fh.bytes_())
    assert (BHOOK - CAVE) + len(bh.bytes_()) <= (FLHOOK - CAVE), "bhook overruns flhook"
    assert (FLHOOK - CAVE) + len(fh.bytes_()) <= 0x660, "flhook overruns cave"
    put(B_S1, struct.pack("<I", (3 << 26) | ((BHOOK >> 2) & 0x03FFFFFF)))  # jal bhook
    put(B_S2, struct.pack("<I", 0))                                        # nop
    put(FL_SITE, struct.pack("<I", (2 << 26) | ((FLHOOK >> 2) & 0x03FFFFFF)))  # j flhook
    open(dst, "wb").write(data)
    print("hwtest written:", dst, "bhook@%#x(%dB) flhook@%#x(%dB)" % (BHOOK, len(bh.bytes_()), FLHOOK, len(fh.bytes_())))


if __name__ == "__main__":
    main()
