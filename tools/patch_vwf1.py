"""True-VWF step 1: per-Latin-glyph flag + REAL dest-width (flush-based).

Two hooks:
  A) blit 0x13A290: for each glyph, set struct+0x1d = 1 for Latin codes
     (0x824F..0x829A fullwidth digits/A-Z/a-z, 0x8140 space) else 0. Free byte.
  B) flush 0x13ACA0 @ 0x13AE5C: the sprite right edge is hardcoded x1 + 0x18
     (`addiu t3,t0,0x17`, t0 = x1+1). When struct+0x1d is set, use +0x0B so the
     sprite dest-width is 0x0C (12px) instead of 0x18 (24px). Y size untouched.

This is the CORRECT dest-width lever (struct+0x10 was a texture reg -> hardware
wash-out). Test with advance/outline still full to confirm it renders clean on
the hardware renderer, then layer advance + outline halving.

Apply after patch_renderer. Hooks live in the setText cave 0x188470.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
CAVE = 0x188470
BHOOK = CAVE + 0x220         # blit flag-set hook (after renderer code+table @ ~0x20A)
FHOOK = CAVE + 0x340         # flush dest-width hook, path A
FHOOK2 = CAVE + 0x380        # flush dest-width hook, path B (dialogue)

# blit sites
B_S1 = 0x13AB68             # lb v1,0x50(s1)
B_S2 = 0x13AB6C             # sb v1,0x1c(s0)
# flush site (path A: struct+0x12 != 0)
F_S1 = 0x13AE5C            # addiu t3,t0,0x17
F_BACK = 0x13AE64
# flush site (path B: struct+0x12 == 0) -- THIS is the dialogue path
F2_S1 = 0x13B304          # addiu t3,t0,0x17
F2_BACK = 0x13B30C

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def sltu(self, d, s, t): self._r(s, t, d, 0, 0x2B)
    def addu(self, d, s, t): self._r(s, t, d, 0, 0x21)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def la(self, t, a): self.lui(t, (a >> 16) & 0xFFFF); self.ori(t, t, a & 0xFFFF)
    def lhu(self, t, o, s): self._i(0x25, s, t, o)
    def lh(self, t, o, s): self._i(0x21, s, t, o)
    def lb(self, t, o, s): self._i(0x20, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def sh(self, t, o, s): self._i(0x29, s, t, o)
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
    def jabs(self, a): self._e(lambda: (2 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jal(self, a): self._e(lambda: (3 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def is_latin(a):
    """emit: t0 = code; result flag in v1 (0/1). clobbers t3,t2,t0. uses at."""
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


def build_bhook():
    a = Asm(BHOOK)
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t2', 4, 'sp'); a.sw('t3', 8, 'sp'); a.sw('t4', 0xC, 'sp')
    a.lb('t4', 0x50, 's1')          # original outline flag
    is_latin(a)                     # v1 = latin flag
    a.sb('v1', 0x13, 's0')          # struct+0x13 = flag (INSIDE copied range; 0x1d was dropped)
    a.beqz('v1', 'keep_outline'); a.nop()
    a.li('t4', 0)                   # Latin -> outline OFF (24px outline smears at 12px pitch)
    a.label('keep_outline')
    a.sb('t4', 0x1c, 's0')          # struct+0x1c
    a.lw('t0', 0, 'sp'); a.lw('t2', 4, 'sp'); a.lw('t3', 8, 'sp'); a.lw('t4', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.nop()
    return a


def build_fhook():
    a = Asm(FHOOK)
    # in: t0 = x1+1 (dest). a3 = struct. s2 already set by entry-j delay slot.
    # out: t3 = t0 + (flag ? 0x0B : 0x17). preserve everything else.
    a.sw('t8', -8, 'sp')
    a.lb('t8', 0x13, 'a3')          # struct+0x13 = latin-letter flag
    a.addiu('t3', 't0', 0x17)       # default: full width
    a.beqz('t8', 'fdone'); a.nop()
    a.addiu('t3', 't0', 0x0B)       # letter: half width
    a.label('fdone')
    a.lw('t8', -8, 'sp')
    a.jabs(F_BACK); a.nop()
    return a


def build_fhook2():
    # dialogue path (0x13B304). in: t0 = x1+1, a3 = struct. out: t3 = width-end.
    a = Asm(FHOOK2)
    a.sw('t8', -8, 'sp')
    a.lb('t8', 0x13, 'a3')          # struct+0x13 = latin-letter flag
    a.addiu('t3', 't0', 0x17)       # default: full width
    a.beqz('t8', 'f2done'); a.nop()
    a.addiu('t3', 't0', 0x0B)       # letter: half width
    a.label('f2done')
    a.lw('t8', -8, 'sp')
    a.jabs(F2_BACK); a.nop()
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b

    bh = build_bhook(); put(BHOOK, bh.bytes_())
    fh = build_fhook(); put(FHOOK, fh.bytes_())
    fh2 = build_fhook2(); put(FHOOK2, fh2.bytes_())
    assert (BHOOK - CAVE) + len(bh.bytes_()) <= (FHOOK - CAVE), "bhook overruns fhook"
    assert (FHOOK - CAVE) + len(fh.bytes_()) <= (FHOOK2 - CAVE), "fhook overruns fhook2"
    assert (FHOOK2 - CAVE) + len(fh2.bytes_()) <= 0x400, "fhook2 overruns advance hook"

    # blit hook: lb v1,0x50(s1) -> jal bhook ; sb v1,0x1c(s0) -> nop
    put(B_S1, struct.pack("<I", (3 << 26) | ((BHOOK >> 2) & 0x03FFFFFF)))
    put(B_S2, struct.pack("<I", 0))
    # flush hook A: addiu t3,t0,0x17 -> j fhook  (delay slot 0x13AE60 preserved)
    put(F_S1, struct.pack("<I", (2 << 26) | ((FHOOK >> 2) & 0x03FFFFFF)))
    # flush hook B (dialogue): addiu t3,t0,0x17 -> j fhook2 (delay 0x13B308 preserved)
    put(F2_S1, struct.pack("<I", (2 << 26) | ((FHOOK2 >> 2) & 0x03FFFFFF)))

    open(dst, "wb").write(data)
    print("VWF step1 written:", dst)
    print("  bhook @%#x (%d B): sets struct+0x1d Latin flag" % (BHOOK, len(bh.bytes_())))
    print("  fhook @%#x (%d B): dest-width +0x0B for Latin" % (FHOOK, len(fh.bytes_())))
    print("  hooks: blit %#x, flush %#x" % (B_S1, F_S1))


if __name__ == "__main__":
    main()
