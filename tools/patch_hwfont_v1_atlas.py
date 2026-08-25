"""HALF-WIDTH FONT (full): expand 1bpp atlas -> PSMCT32 (direct color, no CLUT),
upload to VRAM via PATH2 (VIF1 DIRECT), and redirect Latin dialogue glyphs to it.

Hard-won facts baked in (2026-08-12 live-debug session):
  - li (addiu) SIGN-EXTENDS 0x8xxx immediates: all SJIS constants MUST use ori.
    (The original build's BHOOK never matched a single Latin code because of
    this - the "working" half-width font was actually cache glyphs at halved
    pitch, never the atlas.)
  - PATH3 (D2/GIF) normal-mode DMA from setText never reaches the GS here;
    PATH2 (D1/VIF1) with a DIRECT-wrapped GIF packet works. Pre-wait for
    D1.STR==0 before programming MADR/QWC/CHCR (the game runs its own chains).
    Do NOT hook the flush for per-frame uploads - that wedges the game's VIF
    sync. setText-time upload is safe (verified over many lines).
  - CT32 atlas (ink 0x80000000) sidesteps the PSMT4HL CLUT-index unknowns;
    FLHOOK sets PSM=0 (CT32), CLUT fields are then ignored.
  - Upload re-fires on EVERY setText (per line) so scene loads that stomp the
    VRAM page self-heal on the next line. Expansion runs once (flag-gated).

Chain (applied on top of the fullwidth renderer ELF, patch_renderer):
  setText 0x20C9B0 -> TRAMP: once, expand atlas -> 64KB CT32 IMG @0x1400080;
     every call: PATH2-DMA [VIF DIRECT + GIF A+D + IMAGE] to VRAM TBP0=MYTBP0;
     then j renderer cave 0x188470.
  blit 0x13AB68/6C -> BHOOK: if code is fullwidth Latin (idx 0..61), set flag
     struct+0x13=1, outline off struct+0x1c=0, and override source UV to the atlas
     cell: struct+4 = col*12 - 2048, struct+6 = row*16 - 2048, srcW=srcH=12.
     else keep original outline flag, flag=0.
  flush 0x13B278 -> FLHOOK: if Latin, rewrite stored TEX0 low32: TBP0 -> MYTBP0,
     PSM -> 0 (PSMCT32).  (delay slot 0x13B27C addiu a0,a0,8 already ran.)
  flush 0x13B304 -> FHOOK2: if Latin, dest sprite right edge t0+0x0B (12px) not +0x17.
"""
import sys, struct

VBASE, FOFF, CAVE = 0x100000, 0x1A80, 0x188470
ATLAS_VA = 0x01340000
SCRATCH = 0x01400000
IMG = SCRATCH + 0x80          # 64KB CT32 image (512x32x4)
HDR = SCRATCH + 0x10          # 0x70: VIF qword + GIF header, contiguous with IMG
COLS, CW, CH, VCELL = 42, 12, 12, 16
NGLYPH = 62
MYTBP0 = 0x3400               # VRAM word-page (byte = *256); override via argv[4]
DBW = 8
UPW, UPH = 512, 32
SETTEXT = 0x20C9B0
RENDERER_CAVE = 0x188470
UVBASE = 2048

# cave layout (contiguous after renderer ~0x20A)
TRAMP = CAVE + 0x210
BHOOK = CAVE + 0x3F0
FLHOOK = CAVE + 0x550
FHOOK2 = CAVE + 0x5A0
ADV = CAVE + 0x5C8      # slot reused by UPSTUB (ADV hook itself is retired)
UPSTUB = CAVE + 0x5C8
EXPAND = TRAMP + 0x30      # subroutine inside the TRAMP slot
UP_SITE = 0x10DD68      # post GS-FINISH-wait (safe recurring upload point)
B_S1, B_S2 = 0x13AB68, 0x13AB6C
FL_SITE, FL_RET = 0x13B278, 0x13B280
F2_SITE, F2_BACK = 0x13B304, 0x13B310   # hook displaces BOTH source-edge addius
ADV_SITE, ADV_SITE2 = 0x13AAE8, 0x13AAEC   # addiu v0,v0,0x18 ; lui at,0x7000 (blit pen X)
SADV_SITE = 0x13AB7C                        # addu v1,a0,v1 (shadow pen X accumulate)

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
    def di(self): self._e(lambda: 0x42000039)
    def ei(self): self._e(lambda: 0x42000038)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def sltiu(self, t, s, i): self._i(0x0B, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
    def xori(self, t, s, i): self._i(0x0E, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lhu(self, t, o, s): self._i(0x25, s, t, o)
    def lbu(self, t, o, s): self._i(0x24, s, t, o)
    def lb(self, t, o, s): self._i(0x20, s, t, o)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def sh(self, t, o, s): self._i(0x29, s, t, o)
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
    def jlbl_call(self, a): self._e(lambda: (3 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jlbl(self, l): self._e(lambda _l=l: (2 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build_tramp():
    # setText hook: ensure the CT32 image exists (EXPAND is flag-gated), then
    # continue into the renderer cave. NO DMA HERE - see build_upstub.
    a = Asm(TRAMP)
    a.addiu('sp', 'sp', -0x10)
    a.sw('ra', 0, 'sp')
    a.jlbl_call(EXPAND)
    a.nop()
    a.lw('ra', 0, 'sp')
    a.j(RENDERER_CAVE)
    a.addiu('sp', 'sp', 0x10)                  # (delay)
    return a


def build_expand():
    # Subroutine: if not yet done (flag at SCRATCH), expand the 1bpp atlas to
    # a CT32 image at IMG and copy the GIF header to HDR. Callable from both
    # TRAMP (setText) and UPSTUB (game's texture uploader at boot, which runs
    # BEFORE any setText). Clobbers t0-t9 only besides the saved s-regs.
    a = Asm(EXPAND)
    a.lui('t0', SCRATCH >> 16)
    a.lw('t1', 0, 't0')
    a.bnez('t1', 'edone'); a.nop()
    a.li('t1', 1); a.sw('t1', 0, 't0')
    a.addiu('sp', 'sp', -0x20)
    for i, r in enumerate(['s0', 's1', 's2', 's3', 's4', 's5']):
        a.sw(r, i * 4, 'sp')
    a.la('s1', IMG); a.lui('s2', ATLAS_VA >> 16); a.li('s3', 0)
    a.label('eloop')
    a.li('t0', COLS); a.slt('t1', 's3', 't0')
    a.bnez('t1', 'row0'); a.nop()
    a.addiu('t2', 's3', -COLS); a.li('s4', VCELL); a.jlbl('havecol'); a.nop()
    a.label('row0')
    a.ori('t2', 's3', 0); a.li('s4', 0)
    a.label('havecol')
    a.sll('s5', 't2', 3); a.sll('t4', 't2', 2); a.addu('s5', 's5', 't4')   # base_x = col*12
    a.sll('t3', 's3', 4); a.sll('t4', 's3', 3); a.addu('t3', 't3', 't4'); a.addu('t5', 's2', 't3')  # src = atlas + idx*24
    a.li('t6', 0)
    a.label('pyloop')
    a.li('t8', 0)                              # row bits (0 for pad rows 12..15)
    a.sltiu('t1', 't6', CH)
    a.beqz('t1', 'drow')
    a.sll('t7', 't6', 1)                       # (delay)
    a.addu('t7', 't5', 't7')
    a.lbu('t8', 0, 't7'); a.sll('t8', 't8', 8); a.lbu('t9', 1, 't7'); a.or_('t8', 't8', 't9')
    a.label('drow')
    a.addu('t9', 's4', 't6'); a.sll('t9', 't9', 9); a.addu('t9', 't9', 's5'); a.sll('t9', 't9', 2); a.addu('t9', 't9', 's1')
    a.li('t0', 0)
    a.label('pxloop')
    a.li('t1', 15); a.subu('t1', 't1', 't0'); a.srlv('t2', 't8', 't1'); a.andi('t2', 't2', 1)
    a.sll('t3', 't0', 2); a.addu('t3', 't9', 't3')
    a.bnez('t2', 'pst')
    a.lui('t4', 0x8000)                        # (delay) ink: black, A=0x80
    a.addu('t4', 'zero', 'zero')               # background
    a.label('pst')
    a.sw('t4', 0, 't3')
    a.addiu('t0', 't0', 1); a.li('t1', CW); a.bne('t0', 't1', 'pxloop'); a.nop()
    a.addiu('t6', 't6', 1); a.li('t1', VCELL); a.bne('t6', 't1', 'pyloop'); a.nop()
    a.addiu('s3', 's3', 1); a.li('t1', NGLYPH); a.bne('s3', 't1', 'eloop'); a.nop()
    # copy GIF header (0x70 incl legacy VIF qword) from blob -> HDR
    a.la('s1', ATLAS_VA + NGLYPH * 24); a.la('s2', HDR); a.li('t1', 0x70)
    a.label('hloop')
    a.lw('t0', 0, 's1'); a.sw('t0', 0, 's2'); a.addiu('s1', 's1', 4); a.addiu('s2', 's2', 4); a.addiu('t1', 't1', -4)
    a.bnez('t1', 'hloop'); a.nop()
    for i, r in enumerate(['s0', 's1', 's2', 's3', 's4', 's5']):
        a.lw(r, i * 4, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.label('edone')
    a.jr('ra'); a.nop()
    return a


def build_upstub():
    # Hooked at 0x10DD68: immediately after the game's GS FINISH-wait poll
    # (ld CSR 0x12001000, andi 2 loop) succeeds - the game's own "all GS/DMA
    # work drained" point, reached every frame sync. The ONLY safe moment for
    # a D2 borrow: mid-scene setText uploads corrupted paused game chains ->
    # intermittent hard freezes; the boot-only uploader left the atlas stale.
    # Skips until TRAMP/setText has expanded the image. Scratch: at, t0 only
    # (v0 holds a live value; delay slot 0x10DD6C ori v0 already ran).
    a = Asm(UPSTUB)
    a.lui('t0', SCRATCH >> 16)
    a.lw('t0', 0, 't0')
    a.beqz('t0', 'vsskip'); a.nop()            # image not built yet
    a.lui('at', 0x1001)
    a.la('t0', HDR + 0x10)                     # raw GIF packet (skip VIF qword)
    a.sw('t0', -0x5FF0, 'at')                  # D2_MADR
    a.li('t0', 6 + 4096); a.sw('t0', -0x5FE0, 'at')   # D2_QWC
    a.li('t0', 0x101); a.sw('t0', -0x6000, 'at')      # D2_CHCR kick
    a.lw('t0', -0x6000, 'at')
    a.label('upwait')
    a.andi('t0', 't0', 0x100)
    a.bnez('t0', 'upwait')
    a.lw('t0', -0x6000, 'at')                  # (delay) refetch
    a.label('vsskip')
    a.lui('a0', 0x80)                          # displaced original 0x10DD68
    a.j(0x10DD70)
    a.nop()
    return a


def build_bhook():
    a = Asm(BHOOK)
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.sw('t4', 0x10, 'sp'); a.sw('v1', 0x14, 'sp'); a.sw('at', 0x18, 'sp')
    a.lui('at', 0x7000); a.lhu('t0', 0x60, 'at')      # code
    a.li('v1', -1)
    # digits 0x8250..0x8259 -> 0..9
    a.ori('t1', 'zero', 0x8250); a.slt('t2', 't0', 't1'); a.bnez('t2', 'chk_up'); a.nop()
    a.ori('t1', 'zero', 0x825A); a.slt('t2', 't0', 't1'); a.beqz('t2', 'chk_up'); a.nop()
    a.ori('t1', 'zero', 0x8250); a.subu('v1', 't0', 't1'); a.jlbl('haveidx'); a.nop()
    a.label('chk_up')                                  # A-Z 0x8260..0x8279 -> 10..35
    a.ori('t1', 'zero', 0x8260); a.slt('t2', 't0', 't1'); a.bnez('t2', 'chk_lo'); a.nop()
    a.ori('t1', 'zero', 0x827A); a.slt('t2', 't0', 't1'); a.beqz('t2', 'chk_lo'); a.nop()
    a.ori('t1', 'zero', 0x8260); a.subu('v1', 't0', 't1'); a.addiu('v1', 'v1', 10); a.jlbl('haveidx'); a.nop()
    a.label('chk_lo')                                  # a-z 0x8281..0x829A -> 36..61
    a.ori('t1', 'zero', 0x8281); a.slt('t2', 't0', 't1'); a.bnez('t2', 'notlatin'); a.nop()
    a.ori('t1', 'zero', 0x829B); a.slt('t2', 't0', 't1'); a.beqz('t2', 'notlatin'); a.nop()
    a.ori('t1', 'zero', 0x8281); a.subu('v1', 't0', 't1'); a.addiu('v1', 'v1', 36)
    a.label('haveidx')                                 # v1 = idx 0..61
    a.li('t1', 0xA7); a.sb('t1', 0x13, 's0')          # flag = MAGIC (stale-proof:
    # some glyph builders bypass this blit, leaving garbage in the free byte;
    # flag==1 there made FLHOOK mangle menu JP text. 0xA7 can't occur by luck.)
    a.sb('zero', 0x1c, 's0')                          # outline off
    a.li('t1', COLS); a.slt('t2', 'v1', 't1'); a.bnez('t2', 'r0'); a.nop()
    a.addiu('t3', 'v1', -COLS); a.li('t4', VCELL); a.jlbl('hc'); a.nop()
    a.label('r0'); a.ori('t3', 'v1', 0); a.li('t4', 0)
    a.label('hc')
    # FIELD MAP (from live REGLIST packet decode, 2026-08-12): struct+0/+2 feed
    # the packet's UV slot (SOURCE, +1 bias added by the flush); struct+4/+6
    # (+ globals a1/a2) feed XYZF2 (DEST). The docs had it backwards - writing
    # atlas UVs to +4/+6 moved the sprite off-screen (why the atlas was never
    # visible at ANY VRAM location). So: source cell -> +0/+2, dest untouched.
    a.sll('t1', 't3', 3); a.sll('t2', 't3', 2); a.addu('t1', 't1', 't2')   # col*12
    a.addiu('t1', 't1', -1); a.sh('t1', 0, 's0')                           # src U1 (+1 bias)
    a.addiu('t4', 't4', -1); a.sh('t4', 2, 's0')                           # src V1
    a.li('t1', CW); a.sh('t1', 0xc, 's0'); a.li('t1', CH); a.sh('t1', 0xe, 's0')  # dest W, H(fields)
    a.jlbl('bdone'); a.nop()
    a.label('notlatin')
    a.lb('t1', 0x50, 's1'); a.sb('t1', 0x1c, 's0'); a.sb('zero', 0x13, 's0')
    a.label('bdone')
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
    a.lw('t4', 0x10, 'sp'); a.lw('v1', 0x14, 'sp'); a.lw('at', 0x18, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.nop()
    return a


def build_flhook():
    a = Asm(FLHOOK)
    a.sw('t8', -8, 'sp'); a.sw('at', -0xc, 'sp')
    a.lbu('t8', 0x13, 'a3'); a.xori('t8', 't8', 0xA7); a.bnez('t8', 'fl_ret'); a.nop()
    a.lw('t8', -8, 'a0')                              # TEX0 low32
    a.lui('at', 0xFC0F); a.ori('at', 'at', 0xC000); a.and_('t8', 't8', 'at')   # clear TBP0+PSM
    a.lui('at', MYTBP0 >> 16); a.ori('at', 'at', MYTBP0 & 0xFFFF)              # PSM=0 (CT32)
    a.or_('t8', 't8', 'at'); a.sw('t8', -8, 'a0')
    a.label('fl_ret')
    a.lw('t8', -8, 'sp'); a.lw('at', -0xc, 'sp')
    a.lw('t0', 0x14, 'a3')                            # displaced original
    a.j(FL_RET); a.nop()
    return a


def build_fhook2():
    # Halve BOTH hardcoded source edges (0x17 -> 0x0B) for Latin: horizontal
    # (t3, was at 0x13B304) AND vertical (t6, was at 0x13B30C) - full-height
    # sampling would read the atlas row below the cell. Path-B never uses at,
    # so it serves as the scratch (no spill; slot is exactly 40 bytes).
    a = Asm(FHOOK2)
    a.lbu('at', 0x13, 'a3'); a.xori('at', 'at', 0xA7)
    a.addiu('t3', 't0', 0x17); a.bnez('at', 'f2done')
    a.addiu('t6', 't2', 0x17)                  # (delay)
    a.addiu('t3', 't0', 0x0B); a.addiu('t6', 't2', 0x0B)
    a.label('f2done')
    a.j(F2_BACK); a.nop()
    return a


def build_adv():
    # hook blit pen X advance 0x13AAE8 (addiu v0,v0,0x18). Halve to 0x0C for Latin/
    # space in BOTH passes (no s3 gate: the atlas redirect ignores the cache, so
    # both cache-build and screen passes must use the same tight pitch to avoid
    # ghosting). Restores at=0x70000000 (replaces the nop'd lui at 0x13AAEC).
    a = Asm(ADV)
    a.addiu('sp', 'sp', -0x20)
    a.sw('t0', 0, 'sp'); a.sw('t1', 4, 'sp'); a.sw('t2', 8, 'sp'); a.sw('t3', 0xC, 'sp')
    a.lui('at', 0x7000); a.lhu('t0', 0x60, 'at')
    a.li('t1', 0x18)
    a.ori('t3', 'zero', 0x824F); a.sltu('t2', 't0', 't3')
    a.bnez('t2', 'chk_sp'); a.nop()
    a.ori('t3', 'zero', 0x829B); a.sltu('t2', 't0', 't3')
    a.beqz('t2', 'chk_sp'); a.nop()
    a.li('t1', 0x0C); a.jlbl('apply'); a.nop()
    a.label('chk_sp')
    a.ori('t3', 'zero', 0x8140)
    a.bne('t0', 't3', 'apply'); a.nop()
    a.li('t1', 0x0C)
    a.label('apply')
    a.addu('v0', 'v0', 't1')
    a.lw('t0', 0, 'sp'); a.lw('t1', 4, 'sp'); a.lw('t2', 8, 'sp'); a.lw('t3', 0xC, 'sp')
    a.addiu('sp', 'sp', 0x20)
    a.jr('ra'); a.lui('at', 0x7000)
    return a


def build_sadv(base):
    # hook 0x13AB7C (addu v1,a0,v1): halve the source/2nd pen advance (scratch
    # 0x38, in v1) for EXACTLY the same codes as build_adv (Latin letters AND
    # space 0x8140) so the two pens never drift. The old version skipped the
    # space -> +12px pen drift per space -> interleaved ghosting after the first
    # word. a0 = 2nd pen; jal delay 0x13AB80 (lui at,0x7000) runs; ret 0x13AB84.
    # at is used as scratch, so it MUST be restored to 0x70000000 in our return
    # delay slot: the jal's delay (0x13AB80 lui at,0x7000) runs BEFORE we're
    # entered, and the instruction after return (0x13AB84 sh v1,0x30(at))
    # depends on it. Returning with garbage at = a wild store per glyph
    # (mangled menus, TLB-miss log spam). Same pattern as build_adv.
    a = Asm(base)
    a.sw('t0', -0x10, 'sp')
    a.lui('at', 0x7000); a.lhu('t0', 0x60, 'at')
    a.xori('at', 't0', 0x8140)              # space?
    a.beqz('at', 'shalf')
    a.ori('at', 'zero', 0x824F)             # (delay; Latin base, same range as ADV)
    a.subu('at', 't0', 'at')                # (-0x824F doesn't fit addiu imm16!)
    a.sltiu('at', 'at', 0x4C)
    a.beqz('at', 'sdo'); a.nop()
    a.label('shalf')
    a.ori('v1', 'zero', 0x0C)               # CONSTANT 12 (not srl-halve): the line
    # is drawn in two passes with different base advances (21 and ~42); halving
    # left pass 2 at ~21 -> drifting pale/wide duplicates. A constant pins both.
    a.label('sdo')
    a.addu('v1', 'a0', 'v1')                # displaced original
    a.lw('t0', -0x10, 'sp')
    a.jr('ra'); a.lui('at', 0x7000)         # delay: restore at for 0x13AB84
    return a


def add_ptload(data, blob, vaddr):
    e_phoff = struct.unpack('<I', data[28:32])[0]
    e_phnum = struct.unpack('<H', data[44:46])[0]
    e_phentsize = struct.unpack('<H', data[42:44])[0]
    while len(data) % 0x80:
        data.append(0)
    foff = len(data)
    assert (foff % 0x80) == (vaddr % 0x80)
    data += blob
    ph_new = e_phoff + e_phnum * e_phentsize
    assert ph_new + e_phentsize <= FOFF
    data[ph_new:ph_new + e_phentsize] = struct.pack('<8I', 1, foff, vaddr, vaddr, len(blob), len(blob), 7, 0x80)
    struct.pack_into('<H', data, 44, e_phnum + 1)
    return foff


def build_header():
    def qw(lo, hi=0): return struct.pack("<QQ", lo & (2**64 - 1), hi & (2**64 - 1))
    img_qwc = (UPW * UPH * 4) // 16                             # CT32: 4096
    p = struct.pack("<IIII", 0, 0, 0, 0x50000000 | (6 + img_qwc))  # VIF: NOP,NOP,NOP,DIRECT
    p += qw(4 | (1 << 15) | (1 << 60), 0xE)                     # GIFtag A+D NLOOP=4 NREG=1 REGS=0xE
    p += qw((MYTBP0 << 32) | (DBW << 48) | (0 << 56), 0x50)     # BITBLTBUF DBP/DBW/DPSM=PSMCT32
    p += qw(0, 0x51)                                            # TRXPOS
    p += qw(UPW | (UPH << 32), 0x52)                            # TRXREG W,H
    p += qw(0, 0x53)                                            # TRXDIR host->local
    p += qw((2 << 58) | (1 << 15) | img_qwc, 0)                # GIFtag IMAGE
    assert len(p) == 0x70
    return p


def main():
    global MYTBP0
    src, dst, atlas_bin = sys.argv[1], sys.argv[2], sys.argv[3]
    if len(sys.argv) > 4:
        MYTBP0 = int(sys.argv[4], 0)
    data = bytearray(open(src, "rb").read())
    atlas = open(atlas_bin, "rb").read()
    assert len(atlas) == NGLYPH * 24

    # NO ADV hook: pen-1 is the CACHE-SLOT allocator (not screen pitch); halving
    # it desynced unflagged draws (punctuation) from where the cache-build
    # actually places art -> the neighbor-sliver garbage. Screen pitch for
    # Latin comes from pen-2 (SADV const 12). Leave pen-1 untouched.
    parts = {TRAMP: build_tramp(), EXPAND: build_expand(), BHOOK: build_bhook(),
             FLHOOK: build_flhook(), FHOOK2: build_fhook2(), UPSTUB: build_upstub()}

    def put(v, b):
        o = FOFF + (v - VBASE); data[o:o + len(b)] = b
    ends = sorted(parts.keys())
    for i, base in enumerate(ends):
        code = parts[base].bytes_()
        put(base, code)
        limit = ends[i + 1] if i + 1 < len(ends) else CAVE + 0x660
        assert (base - CAVE) + len(code) <= (limit - CAVE), "cave overlap at %#x (%dB, next %#x)" % (base, len(code), limit)
    # hooks
    put(B_S1, struct.pack("<I", (3 << 26) | ((BHOOK >> 2) & 0x03FFFFFF)))   # jal bhook
    put(B_S2, struct.pack("<I", 0))
    put(FL_SITE, struct.pack("<I", (2 << 26) | ((FLHOOK >> 2) & 0x03FFFFFF)))
    put(F2_SITE, struct.pack("<I", (2 << 26) | ((FHOOK2 >> 2) & 0x03FFFFFF)))
    put(SETTEXT, struct.pack("<I", (2 << 26) | ((TRAMP >> 2) & 0x03FFFFFF)))
    put(UP_SITE, struct.pack("<I", (2 << 26) | ((UPSTUB >> 2) & 0x03FFFFFF)))  # j upstub
    # PT_LOAD: atlas + header + shadow-advance hook (cave is full)
    sadv_va = ATLAS_VA + NGLYPH * 24 + 0x70   # after the VIF+GIF header
    sadv = build_sadv(sadv_va).bytes_()
    put(SADV_SITE, struct.pack("<I", (3 << 26) | ((sadv_va >> 2) & 0x03FFFFFF)))  # jal sadv
    blob = bytearray(atlas) + build_header() + sadv
    foff = add_ptload(data, blob, ATLAS_VA)
    newsz = len(data)
    assert newsz <= 0x350000, "ELF past sector limit %#x" % newsz
    open(dst, "wb").write(data)
    print("hwfont written:", dst, "ELF=%#x" % newsz)
    for base in ends:
        print("  cave %#x: %d B" % (base, len(parts[base].bytes_())))
    print("  PT_LOAD @%#x foff %#x (%d B), TBP0=%d" % (ATLAS_VA, foff, len(blob), MYTBP0))


if __name__ == "__main__":
    main()
