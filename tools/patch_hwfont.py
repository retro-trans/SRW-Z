"""HALF-WIDTH FONT v2 - MASTER-FONT ARCHITECTURE (the validated design).

Instead of a custom VRAM atlas (unwinnable: every VRAM page is contested by
RTs/scene streams, and any DMA upload from game code eventually deadlocks the
engine's paused chains), the half-width letterforms are STAMPED directly into
the game's decoded master font in RAM. The engine then rasterizes, caches,
uploads and colors them through its normal pipeline - identical ink/outline
color to the Japanese text, zero DMA, zero VRAM management.

Validated facts (2026-08-12 live session):
  - Decoded master font: linear array of 24x24 4bpp cells, 288B each (12B/row,
    LOW nibble = even x) at RAM 0x9AE610.
    cell(code) = 0x9AE610 + ((lead-0x81)*192 + trail-0x40) * 288
    (192 cells per lead row, NO 0x7F-gap skip; anchor: cell 57 = 0x8179).
  - Cells are demand-decoded (0x1C6C40) on a glyph's first display, which can
    overwrite a stamp -> the stamp routine runs at EVERY setText (pure RAM
    stores, ~0.1ms) so any reverted cell heals on the next line.
  - Glyph baseline in master cells ~ row 21. Our 12x16 art (baseline row 13)
    is stamped at cell rows 8..23; rows 0..7 (cols 0-11) are cleared.
  - ASCII punctuation . " ' ! , - ? is remapped (patch_renderer table at
    0x1885BC) to unused SJIS 0x8240..0x8246 so the whole half-width set is one
    contiguous code range 0x8240..0x829A (punct+digits+letters).

Hooks (applied on top of the fullwidth renderer ELF, patch_renderer):
  setText 0x20C9B0 -> TRAMP: stamp all 69 half-width cells into the master
     font (idempotent), then j renderer cave 0x188470.
  blit 0x13AB68/6C -> BHOOK: code in 0x8240..0x829A -> flag struct+0x13=0xA7,
     outline off +0x1c=0, dest W/H (+0xc/+0xe) = 12. NO UV writes: struct+0/+2
     (source = cache slot, pen 1) and +4/+6 (dest, pen 2) stay engine-managed.
  blit pen2 0x13AB7C -> SADV: dest advance = constant 12 for range + space.
  flush 0x13B304 -> FHOOK2: flagged -> HORIZONTAL source edge t0+0x0B (12px);
     vertical edge stays 0x17 (full 24-row cell). Returns to 0x13B310.
  (No FLHOOK/TEX0 rewrite, no atlas upload, no DMA - all removed.)

MIPS gotchas honored: li/addiu sign-extends 0x8xxx (use ori); jal/branch delay
slots run BEFORE the target; $at must be restored for 0x13AB84 (sh v1,0x30(at)).
"""
import sys, struct

VBASE, FOFF, CAVE = 0x100000, 0x1A80, 0x78A070  # see patch_renderer.CAVE:
# the cave sits in the gap between the end of the image (0x789D00) and the heap
# base, which patch_renderer moves up to 0x790000 so sbrk can never reach it.
# The old 0x1600070 was inside the heap and got handed out mid-battle.
# MUST stay in sync with patch_renderer.CAVE.
ATLAS_VA = CAVE + 0x540  # atlas right after the renderer+hook layout
                         # (cave spans 6328B; layout+atlas ~= 0xD97B used).
NGLYPH = 138                  # 69 regular + 69 bold (menu) glyphs
GLYPH_BYTES = 72              # 24 rows x 3B (12px at 2bpp, MSB-first)
NART = 69                     # stored glyph arts (bold made at stamp time)
HW_BASE = 0x8540              # private half-width range 0x8540..0x8584 (69):
                              # SJIS lead 0x85 is a fully UNASSIGNED row, so
                              # native fullwidth text (menus use 0x824F-0x829A
                              # digits/letters!) never collides with our cells.
# The decoded master font is allocated on the heap - 0x9AE610 was only ever the
# address it happened to land at with the stock heap base, and it MOVES if the
# heap base moves (which is how the v1.29 cave fix made all our glyphs vanish).
# The engine keeps the buffer's address in this BSS global, whose own address is
# fixed by the linker and so is safe to hardcode. Verified equal to 0x9AE610 in
# all five save states; 0x46E3B0 next to it holds the line canvas (0x990600).
FONTPTR = 0x0046E3A8          # u32: base of the decoded master font
LATIN_OFF = 768 * 288         # cell of code 0x8540 ((0x85-0x81)*192 cells in)
MASTER_LATIN = 0x9AE610 + LATIN_OFF   # stock-heap value, for reference only
SETTEXT = 0x20C9B0
RENDERER_CAVE = CAVE
TBL = CAVE + 0x14C            # patch_renderer's ASCII->fullwidth table (code=332B)

# cave layout (no setText TRAMP anymore: stamping happens per-glyph in BHOOK)
BHOOK = CAVE + 0x210          # big slot to +0x440 (560B) - includes the stamper
SADV = CAVE + 0x440           # slot to +0x490
FHOOK2 = CAVE + 0x490         # slot to +0x4B8
MHOOK = CAVE + 0x4B8          # slot to +0x530: menu/global ASCII->code remap
ADV2 = CAVE + 0x5C8           # slot to +0x660: pen-1 (cache slot) advance
B_S1, B_S2 = 0x13AB68, 0x13AB6C
ADV_SITE, ADV_SITE2 = 0x13AAE8, 0x13AAEC   # addiu v0,v0,0x18 ; lui at,0x7000
F2_SITE, F2_BACK = 0x13B304, 0x13B310
SADV_SITE = 0x13AB7C
M_SITE, M_BACK = 0x13A7A0, 0x13A7A8   # blit code-stash: lui at/sh v0,0x60(at)

# ASCII -> private half-width codes, one per atlas glyph (order: ."'!,-? 0-9 A-Z a-z)
HW_MAP = [(c, HW_BASE + g) for g, c in enumerate(
    [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] +
    list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)))]

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
    def or_(self, d, s, t): self._r(s, t, d, 0, 0x25)
    def slt(self, d, s, t): self._r(s, t, d, 0, 0x2A)
    def movz(self, d, s, t): self._r(s, t, d, 0, 0x0A)
    def movn(self, d, s, t): self._r(s, t, d, 0, 0x0B)
    def mult(self, s, t): self._r(s, t, 'zero', 0, 0x18)
    def mflo(self, d): self._r('zero', 'zero', d, 0, 0x12)
    def sll(self, d, t, sa): self._r('zero', t, d, sa, 0)
    def srl(self, d, t, sa): self._r('zero', t, d, sa, 2)
    def srlv(self, d, t, s): self._r(s, t, d, 0, 6)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
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
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def build_bhook():
    # jal'd from B_S1 per glyph (displaced originals: lb v1,0x50(s1);
    # sb v1,0x1c(s0)). Codes 0x8540..0x85C9: 0-68 regular (dialogue),
    # 69-137 BOLD (menu; same art, dilated 1px right via per-level MAX).
    # Art is 2bpp grayscale, expanded to 4bpp nibbles 0/5/10/15 so the
    # letters carry antialiased edges like the JP master-font glyphs.
    a = Asm(BHOOK)
    a.lui('t1', 0x7000)
    a.lhu('t0', 0x60, 't1')
    a.ori('t1', 'zero', HW_BASE)
    a.subu('t1', 't0', 't1')
    a.sltiu('t2', 't1', NGLYPH)
    a.beqz('t2', 'notl'); a.nop()
    a.li('t2', 0xA7); a.sb('t2', 0x13, 's0')
    a.lb('t2', 0x50, 's1')
    a.sb('t2', 0x1c, 's0')
    a.li('t2', 12)
    a.sh('t2', 0xc, 's0')
    a.sltiu('t9', 't1', NART)
    a.xori('t9', 't9', 1)
    a.addu('t2', 't1', 'zero')
    a.beqz('t9', 'artok'); a.nop()
    a.addiu('t2', 't1', -NART)
    a.label('artok')
    a.sll('t3', 't1', 8); a.sll('t5', 't1', 5); a.addu('t3', 't3', 't5')
    # The decoded master font is a HEAP allocation, so its address moves with
    # the heap base - hardcoding it broke every glyph the moment patch_renderer
    # moved the heap off _end. Read the engine's own pointer instead (t5 is
    # free here; it is reassigned for the atlas below).
    a.lui('t4', (FONTPTR + 0x8000) >> 16)
    a.lw('t4', FONTPTR - (((FONTPTR + 0x8000) >> 16) << 16), 't4')
    a.beqz('t4', 'bdone'); a.nop()      # font not decoded yet: skip the stamp
    a.lui('t5', LATIN_OFF >> 16); a.ori('t5', 't5', LATIN_OFF & 0xFFFF)
    a.addu('t4', 't4', 't5')
    a.addu('t4', 't4', 't3')
    a.sll('t3', 't2', 6); a.sll('t6', 't2', 3)
    a.addu('t3', 't3', 't6')                    # *72
    a.lui('t5', ATLAS_VA >> 16); a.ori('t5', 't5', ATLAS_VA & 0xFFFF)
    a.addu('t5', 't5', 't3')
    a.li('t7', 24)                              # full 24-row native art
    a.bnez('t9', 'brl'); a.nop()
    # regular rows
    a.label('rl')
    a.lbu('t1', 0, 't5'); a.sll('t1', 't1', 16)
    a.lbu('t2', 1, 't5'); a.sll('t2', 't2', 8)
    a.or_('t1', 't1', 't2')
    a.lbu('t2', 2, 't5')
    a.or_('t0', 't1', 't2')
    a.li('t8', 22)
    a.li('t6', 0)
    a.label('xp')
    a.srlv('t2', 't0', 't8'); a.andi('t2', 't2', 3)
    a.sll('t9', 't2', 2); a.addu('t2', 't9', 't2')
    a.addiu('t8', 't8', -2)
    a.srlv('t9', 't0', 't8'); a.andi('t9', 't9', 3)
    a.sll('t1', 't9', 2); a.addu('t9', 't1', 't9')
    a.sll('t9', 't9', 4)
    a.or_('t2', 't2', 't9')
    a.addu('t1', 't4', 't6')
    a.sb('t2', 0, 't1')
    a.addiu('t6', 't6', 1)
    a.addiu('t8', 't8', -2)
    a.sltiu('t1', 't6', 6)
    a.bnez('t1', 'xp'); a.nop()
    a.addiu('t4', 't4', 12)
    a.addiu('t5', 't5', 3)
    a.addiu('t7', 't7', -1)
    a.bnez('t7', 'rl'); a.nop()
    a.beq('zero', 'zero', 'bdone'); a.nop()
    # bold rows (dilate 1px right, per-level max)
    a.label('brl')
    a.lbu('t1', 0, 't5'); a.sll('t1', 't1', 16)
    a.lbu('t2', 1, 't5'); a.sll('t2', 't2', 8)
    a.or_('t1', 't1', 't2')
    a.lbu('t2', 2, 't5')
    a.or_('t0', 't1', 't2')
    a.li('t8', 22)
    a.li('t6', 0)
    a.li('t3', 0)
    a.label('xpb')
    a.srlv('t2', 't0', 't8'); a.andi('t2', 't2', 3)
    a.addu('t9', 't2', 'zero')
    a.slt('t1', 't9', 't3')
    a.movn('t9', 't3', 't1')
    a.addu('t3', 't2', 'zero')
    a.sll('t1', 't9', 2); a.addu('t9', 't1', 't9')
    a.addu('t1', 't4', 't6')
    a.sb('t9', 0, 't1')
    a.addiu('t8', 't8', -2)
    a.srlv('t2', 't0', 't8'); a.andi('t2', 't2', 3)
    a.addu('t9', 't2', 'zero')
    a.slt('t1', 't9', 't3')
    a.movn('t9', 't3', 't1')
    a.addu('t3', 't2', 'zero')
    a.sll('t1', 't9', 2); a.addu('t9', 't1', 't9')
    a.sll('t9', 't9', 4)
    a.addu('t1', 't4', 't6')
    a.lbu('t2', 0, 't1')
    a.or_('t9', 't9', 't2')
    a.sb('t9', 0, 't1')
    a.addiu('t6', 't6', 1)
    a.addiu('t8', 't8', -2)
    a.sltiu('t1', 't6', 6)
    a.bnez('t1', 'xpb'); a.nop()
    a.addiu('t4', 't4', 12)
    a.addiu('t5', 't5', 3)
    a.addiu('t7', 't7', -1)
    a.bnez('t7', 'brl'); a.nop()
    a.beq('zero', 'zero', 'bdone'); a.nop()
    a.label('notl')
    a.lb('t1', 0x50, 's1'); a.sb('t1', 0x1c, 's0')
    a.sb('zero', 0x13, 's0')
    a.label('bdone')
    a.jr('ra'); a.nop()
    return a

def build_sadv():
    # jal'd from SADV_SITE 0x13AB7C (delay 0x13AB80 lui at ran BEFORE entry).
    # Dest-pen advance = constant 12 for the half-width range + space; must
    # return with at = 0x70000000 for 0x13AB84 (sh v1,0x30(at)).
    a = Asm(SADV)
    a.sw('t0', -0x10, 'sp')
    a.lui('at', 0x7000)
    a.lhu('t0', 0x60, 'at')
    a.xori('at', 't0', 0x8140)                  # space?
    a.beqz('at', 'shalf')
    a.ori('at', 'zero', HW_BASE)                # (delay)
    a.subu('at', 't0', 'at')
    a.sltiu('at', 'at', NGLYPH)
    a.beqz('at', 'sdo'); a.nop()
    # (fallthrough = halfwidth letter)
    # halfwidth letter: advance = stored dest W (already halved by BHOOK,
    # so row-proportional) + 1px letterspacing. Reading the STRUCT (s0) gives
    # the SAME value to both draw passes - scaling each pass's own base
    # advance desynced them (fill/outline interleave, 'Bcrus' artifact).
    a.lhu('t0', 0xc, 's0')
    a.beq('zero', 'zero', 'sdo')
    a.addiu('v1', 't0', 1)                      # (delay)
    a.label('shalf')
    a.ori('v1', 'zero', 0x0D)                   # space: proven constant
    a.label('sdo')
    a.addu('v1', 'a0', 'v1')                    # displaced original
    a.lw('t0', -0x10, 'sp')
    a.jr('ra'); a.lui('at', 0x7000)             # delay: restore at
    return a


def build_adv2():
    # jal'd from ADV_SITE (its old delay 0x13AAEC lui at,0x7000 is nop'd; we
    # restore at in our return delay). Pen-1 = the CACHE-SLOT allocator: at
    # the stock 0x18/glyph, long English lines overflow the 504-unit slot row
    # mid-line and burn 2-3 cache rows each -> the allocator exhausts after
    # ~25 lines and spins forever (the deep-in-scene freezes). 12/glyph for
    # the half-width range keeps every line in one row. Safe now that ALL our
    # chars (punct included) are flagged/stamped - nothing unflagged samples
    # letter slots anymore.
    a = Asm(ADV2)
    a.sw('t0', -0x10, 'sp')
    a.lui('at', 0x7000)
    a.lhu('t0', 0x60, 'at')
    a.xori('at', 't0', 0x8140)                  # space?
    a.beqz('at', 'ahalf')
    a.ori('at', 'zero', HW_BASE)                # (delay)
    a.subu('at', 't0', 'at')
    a.sltiu('at', 'at', NGLYPH)
    a.bnez('at', 'ahalf'); a.nop()
    a.addiu('v0', 'v0', 0x18)                   # normal advance
    a.beq('zero', 'zero', 'adone'); a.nop()
    a.label('ahalf')
    a.addiu('v0', 'v0', 0x0C)
    a.label('adone')
    a.lw('t0', -0x10, 'sp')
    a.jr('ra'); a.lui('at', 0x7000)             # delay: restore at
    return a


def build_fhook2():
    # j'd from F2_SITE (delay 0x13B308 dsll t4,t0,4 ran). Halve ONLY the
    # horizontal source edge for flagged glyphs; vertical stays 0x17 (cells
    # are full 24 rows). Path-B never uses at.
    # TWO conditions, not one. struct+0x13 == 0xA7 alone is NOT safe: glyph
    # builders that bypass the blit never run BHOOK, so they inherit whatever
    # that byte held - and after any of our text draws, it holds 0xA7. A stale
    # flag makes us halve a FOREIGN glyph's source edge, i.e. emit a sprite with
    # geometry that does not match its texture. That is a plausible route from
    # guest data to the HOST access violations seen crashing PCSX2 during battle
    # animations (the Japanese disc never crashes; ours does, intermittently,
    # and once it starts every animation dies).
    # BHOOK also writes struct+0xc = 12 for our glyphs, so require that too -
    # a stale 0xA7 on a foreign glyph will almost never also have destW 12.
    # Branch-free via movz so both tests fit the 40-byte slot. t6 doubles as
    # scratch before it is given its real value in the jump's delay slot.
    a = Asm(FHOOK2)
    a.lbu('at', 0x13, 'a3'); a.xori('at', 'at', 0xA7)   # 0 if the flag matches
    a.lhu('t6', 0xc, 'a3'); a.xori('t6', 't6', 12)      # 0 if destW is ours
    a.or_('at', 'at', 't6')                             # 0 only if BOTH match
    a.addiu('t3', 't0', 0x17)                           # default: full edge
    a.addiu('t6', 't0', 0x0B)                           # candidate: halved
    a.movz('t3', 't6', 'at')                            # take it only if at==0
    a.j(F2_BACK)
    a.addiu('t6', 't2', 0x17)                # (delay) vertical: always full
    return a


def build_mhook():
    # j'd from M_SITE 0x13A7A0 (delay slot = the original sh v0,0x60(at); at
    # still holds 0x70000000). The string reader 0x13A290 consumes NON-control
    # bytes as UNCONDITIONAL 2-byte pairs (s4 = read ptr, verified untouched
    # from pair-fetch to the stash), so raw ASCII arrives as garbage pairs
    # like 0x5072 'Pr' and gets lead-checked away - that is why ASCII was
    # invisible in menus. Fix: if the HIGH byte is printable ASCII, remap IT
    # through patch_renderer's TBL (letters -> private half-width codes,
    # symbols -> fullwidth) and GIVE BACK the low byte (s4 -= 1). Bytes
    # 0x2E-0x3D never reach here (control codes - encode those chars
    # fullwidth in data, patch.py mode "menu"). Dialogue arrives pre-mapped
    # (setText cave) with lead 0x85, so this never double-fires.
    a = Asm(MHOOK)
    a.srl('t1', 'v0', 8)                        # high byte
    a.addiu('t2', 't1', -0x20)
    a.sltiu('t3', 't2', 0x5F)                   # printable ASCII (incl space)?
    a.beqz('t3', 'mdone'); a.nop()
    a.sll('t2', 't2', 1)
    a.lui('t3', TBL >> 16); a.ori('t3', 't3', TBL & 0xFFFF)
    a.addu('t3', 't3', 't2')
    a.lbu('t4', 0, 't3'); a.lbu('t2', 1, 't3')  # big-endian lead,trail
    a.sll('t4', 't4', 8)
    a.or_('v0', 't4', 't2')
    a.lui('at', 0x7000)
    a.sh('v0', 0x60, 'at')                      # re-store remapped code
    a.addiu('s4', 's4', -1)                     # un-consume the low byte
    a.label('mdone')
    a.j(M_BACK); a.nop()
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


def main():
    src, dst, atlas_bin = sys.argv[1], sys.argv[2], sys.argv[3]
    nopunct = "--nopunct" in sys.argv
    nosadv = "--nosadv" in sys.argv
    nohooks = "--nohooks" in sys.argv
    noatlas = "--noatlas" in sys.argv
    data = bytearray(open(src, "rb").read())
    atlas = open(atlas_bin, "rb").read()
    assert len(atlas) == NART * GLYPH_BYTES, len(atlas)

    parts = {BHOOK: build_bhook(), SADV: build_sadv(), FHOOK2: build_fhook2(),
             MHOOK: build_mhook()}

    def put(v, b):
        # resolve through the PT_LOAD table: hooks live in the main image, the
        # cave/atlas live in the segment patch_renderer appended
        phoff = struct.unpack_from("<I", data, 28)[0]
        phnum = struct.unpack_from("<H", data, 44)[0]
        ent = struct.unpack_from("<H", data, 42)[0]
        for k in range(phnum):
            t, off, va, pa, fsz, msz, fl, al = struct.unpack_from("<8I", data, phoff + k*ent)
            if t == 1 and fsz and va <= v < va + fsz:
                o = off + (v - va)
                data[o:o + len(b)] = b
                return
        raise KeyError("vaddr %#x is not in any PT_LOAD" % v)
    limits = {BHOOK: CAVE + 0x440, SADV: FHOOK2, FHOOK2: MHOOK,
              MHOOK: CAVE + 0x530}
    for base, asm in parts.items():
        code = asm.bytes_()
        assert base + len(code) <= limits[base], \
            "cave overlap at %#x (%dB, limit %#x)" % (base, len(code), limits[base])
        put(base, code)
    # hooks
    if not nohooks:
        put(B_S1, struct.pack("<I", (3 << 26) | ((BHOOK >> 2) & 0x03FFFFFF)))   # jal bhook
        put(B_S2, struct.pack("<I", 0))
        put(F2_SITE, struct.pack("<I", (2 << 26) | ((FHOOK2 >> 2) & 0x03FFFFFF)))
        put(M_SITE, struct.pack("<I", (2 << 26) | ((MHOOK >> 2) & 0x03FFFFFF)))
    if not nosadv:
        put(SADV_SITE, struct.pack("<I", (3 << 26) | ((SADV >> 2) & 0x03FFFFFF)))
    # setText keeps patch_renderer's own hook (j renderer cave) - no TRAMP
    # remap ALL 69 dialogue chars to the private range (big-endian lead,trail)
    if not nopunct:
        for ascii_c, code in HW_MAP:
            put(TBL + (ascii_c - 0x20) * 2, bytes([code >> 8, code & 0xFF]))
    # atlas -> the second dead-code cave (inside the existing big segment;
    # NO new PT_LOAD - see ATLAS_VA comment)
    # Cave end is CAVE-relative: hardcoding the old 0x1230C0 here is what broke
    # the font the first time the cave was relocated (atlas landed at the old
    # address while the hooks read the new one).
    assert ATLAS_VA + len(atlas) <= CAVE + 0x18B0, "atlas past cave end"
    if not noatlas:
        put(ATLAS_VA, atlas)
    newsz = len(data)
    assert newsz <= 0x350000, "ELF past sector limit %#x" % newsz
    open(dst, "wb").write(data)
    print("hwfont v2 (master-font) written:", dst, "ELF=%#x" % newsz)
    for base, asm in sorted(parts.items()):
        print("  cave %#x: %d B" % (base, len(asm.bytes_())))
    print("  atlas in dead-code cave @%#x (%d B)" % (ATLAS_VA, len(atlas)))
    print("  remapped %d chars to %#x..%#x" % (len(HW_MAP), HW_MAP[0][1], HW_MAP[-1][1]))


if __name__ == "__main__":
    main()
