"""Investigation logger: capture the FULL per-glyph struct at blit time to free
EE RAM (0x1400000), so PINE can read the real texture-base + UV values that the
flush consumes. NO width change -> logs clean FULLWIDTH values. Apply on top of
patch_renderer only.

Hook: 0x13AB68 (lb v1,0x50(s1)) -> jal LOGHOOK ; 0x13AB6C (sb v1,0x1c(s0)) -> nop
LOGHOOK reimplements the outline-flag copy (struct+0x1c = s1+0x50), then appends
one 16-byte record per glyph to the ring at LOGBUF:
  +0  count (u32)
  +4  N x 16B: [u16 destX][u16 destY][u16 srcU][u16 srcV]
               [u16 srcW][u16 srcH][u8 s+0x10][u8 s+0x11][u16 code]
"""
import sys, struct

VBASE, FOFF, CAVE = 0x100000, 0x1A80, 0x188470
HOOK = CAVE + 0x220          # reuse the vwf1 bhook slot (we're not applying vwf1)
LOGBUF = 0x01400000          # free EE RAM; PINE reads it live
NENT = 64
B_S1 = 0x13AB68              # lb v1,0x50(s1)
B_S2 = 0x13AB6C              # sb v1,0x1c(s0)

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
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
    def lbu(self, t, o, s): self._i(0x24, s, t, o)
    def lb(self, t, o, s): self._i(0x20, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def sh(self, t, o, s): self._i(0x29, s, t, o)
    def sb(self, t, o, s): self._i(0x28, s, t, o)
    def la(self, t, a): self.lui(t, (a >> 16) & 0xFFFF); self.ori(t, t, a & 0xFFFF)
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build():
    a = Asm(HOOK)
    # original outline-flag copy: struct+0x1c = (s8) s1+0x50
    a.lb('v1', 0x50, 's1'); a.sb('v1', 0x1c, 's0')
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.la('t0', LOGBUF)
    a.lw('t1', 0, 't0')                 # count
    a.andi('t2', 't1', NENT - 1)
    a.sll('t2', 't2', 4)                # *16
    a.addiu('t3', 't0', 4); a.addu('t3', 't3', 't2')   # entry ptr
    a.lhu('t2', 0, 's0'); a.sh('t2', 0, 't3')     # destX
    a.lhu('t2', 2, 's0'); a.sh('t2', 2, 't3')     # destY
    a.lhu('t2', 4, 's0'); a.sh('t2', 4, 't3')     # srcU
    a.lhu('t2', 6, 's0'); a.sh('t2', 6, 't3')     # srcV
    a.lhu('t2', 0xc, 's0'); a.sh('t2', 8, 't3')   # srcW
    a.lhu('t2', 0xe, 's0'); a.sh('t2', 0xa, 't3') # srcH
    a.lbu('t2', 0x10, 's0'); a.sb('t2', 0xc, 't3')  # struct+0x10
    a.lbu('t2', 0x11, 's0'); a.sb('t2', 0xd, 't3')  # struct+0x11
    a.lui('t2', 0x7000); a.lhu('t2', 0x60, 't2'); a.sh('t2', 0xe, 't3')  # code
    a.addiu('t1', 't1', 1); a.sw('t1', 0, 't0')   # count++
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
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
    put(B_S1, struct.pack("<I", (3 << 26) | ((HOOK >> 2) & 0x03FFFFFF)))  # jal HOOK
    put(B_S2, struct.pack("<I", 0))                                       # nop
    assert (HOOK - CAVE) + len(code) <= 0x400, "hook overruns cave region"
    open(dst, "wb").write(data)
    print("flushlog written:", dst, "hook @%#x (%dB) LOGBUF @%#x" % (HOOK, len(code), LOGBUF))


if __name__ == "__main__":
    main()
