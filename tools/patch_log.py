"""Instrument the glyph blit to log per-glyph dest+source coords to a RAM ring
buffer, so PINE can read the exact numbers.

Buffer at LOGBUF = cave+0x400:
  +0x00  u32 count (increments per glyph drawn; init 0 in ELF)
  +0x04  64 entries x 8 bytes: [u16 dest_x=struct+0][u16 struct+4][u16 struct+6][u16 code]
Ring: slot = count & 63. After a dialogue line renders, the last <=64 slots hold
that line's glyphs.

Hook at the blit's struct+0x1c write (0x13AB68/0x13AB6C): at that point struct+0
(dest x), struct+4/+6 (source word from scratch 0x30) are all set, and scratch
0x60 holds the 2-byte glyph code. Apply on top of patch_renderer.
"""
import sys, struct

VBASE = 0x100000
FOFF = 0x1A80
CAVE = 0x188470
HOOK = CAVE + 0x480          # coexists with vwf1(0x220,0x340)+advance(0x400)
LOGBUF = CAVE + 0x510        # count + 32*8 entries -> ends 0x614, INSIDE 0x660 cave
B_S1 = 0x13AB40              # sw v1,0xc(s0)   (original preserved in hook)
B_S2 = None                  # single-instruction hook (delay slot 0x13AB44 = lui at,0x7000)
NENT = 32                    # ring slots; MUST be power-of-2 (mask = NENT-1)

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _b(self, op, rs, rt, lbl):
        idx = len(self.ins)
        def f(_i=idx, _op=op, _rs=rs, _rt=rt, _l=lbl):
            off = (self.labels[_l] - (self.base + _i * 4 + 4)) >> 2
            return (_op << 26) | (R[_rs] << 21) | (R[_rt] << 16) | (off & 0xFFFF)
        self._e(f)
    def beqz(self, s, l): self._b(4, s, 'zero', l)
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def addu(self, d, s, t): self._r(s, t, d, 0, 0x21)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
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
    def sh(self, t, o, s): self._i(0x29, s, t, o)
    def sb(self, t, o, s): self._i(0x28, s, t, o)
    def la(self, t, a): self.lui(t, (a >> 16) & 0xFFFF); self.ori(t, t, a & 0xFFFF)
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build():
    a = Asm(HOOK)
    a.sw('v1', 0xc, 's0')             # ORIGINAL: struct+0xc = scratch 0x3c (source width)
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp'); a.sw('t9', 0x10, 'sp')
    a.beqz('s3', 'skip'); a.nop()     # s3==0 => atlas build: DON'T log (screen only)
    a.la('t9', LOGBUF)
    a.lw('t0', 0, 't9')               # count
    a.andi('t1', 't0', NENT - 1)      # slot (ring mask; NENT power-of-2)
    a.sll('t1', 't1', 3)              # *8
    a.addiu('t2', 't9', 4)
    a.addu('t2', 't2', 't1')          # entry ptr
    a.lhu('t3', 0, 's0'); a.sh('t3', 0, 't2')    # dest x (struct+0)
    a.lhu('t3', 4, 's0'); a.sh('t3', 2, 't2')    # struct+4 (source U)
    a.lhu('t3', 0xc, 's0'); a.sh('t3', 4, 't2')  # struct+0xc (source width)
    a.lui('t1', 0x7000); a.lhu('t3', 0x60, 't1'); a.sh('t3', 6, 't2')  # code
    a.addiu('t0', 't0', 1); a.sw('t0', 0, 't9')  # count++
    a.label('skip')
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp'); a.lw('t9', 0x10, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.nop()
    return a


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    code = build().bytes_()

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    put(HOOK, code)
    put(LOGBUF, b"\x00" * 4)                     # init count=0
    put(B_S1, struct.pack("<I", (3 << 26) | ((HOOK >> 2) & 0x03FFFFFF)))  # jal
    if B_S2 is not None:
        put(B_S2, struct.pack("<I", 0))          # nop
    assert (HOOK - CAVE) + len(code) <= (LOGBUF - CAVE), "hook overruns log buffer"
    assert (NENT & (NENT - 1)) == 0, "NENT must be power-of-2 for the ring mask"
    buf_end = (LOGBUF - CAVE) + 4 + NENT * 8
    assert buf_end <= 0x660, "LOG BUFFER OVERRUNS CAVE (0x%x > 0x660) -> corrupts live code!" % buf_end
    open(dst, "wb").write(data)
    print("log patch written:", dst)
    print("  hook @%#x (%d B); LOGBUF @%#x (EE addr for PINE)" % (HOOK, len(code), LOGBUF))


if __name__ == "__main__":
    main()
