"""ASCII -> fullwidth glyph renderer patch for SRW Z (SLPS-25887).

The dialogue font only has 2-byte fullwidth SJIS glyphs; raw half-width ASCII
renders as blank boxes (see docs/RENDERER.md). This patch hooks
`MessageWindow::setText` (0x20C9B0) and, while copying the line into the message
object (RAM scratch, NOT the offset-constrained scenario data), converts every
half-width ASCII byte to its fullwidth-SJIS twin. The existing renderer already
draws fullwidth perfectly.

Conversion is per-character so mixed lines work (e.g. English body + a Japanese
$-macro name): 2-byte SJIS and half-width kana pass through untouched, 0x0A / low
control bytes pass through, printable ASCII 0x20..0x7E -> fullwidth via a table.

Everything (hook trampoline, converter, table, scratch buffer) lives in a code
cave in unused ELF padding, so no addresses shift and no other file changes.
"""
import sys
import struct

# ---- fixed engine addresses (EE vaddr, boot ELF SLPS_258.87) ----
SETTEXT   = 0x20C9B0   # MessageWindow::setText(this=a0, src=a1)  -- hook here
NEEDEXP   = 0x200F80   # returns v0 = expand-context (0 => plain copy)
EXPAND    = 0x2011D0   # expand(a0=ctx, a1=dst, a2=src)
STRCPY    = 0x1A0D88   # strcpy(a0=dst, a1=src)
VBASE     = 0x100000   # PT_LOAD vaddr
FOFF      = 0x1A80     # PT_LOAD file offset

# ---- where the cave lives, and why it is safe there ----
#
# crt0 runs InitHeap(_end, -1) at 0x1001D0, so the PS2 kernel heap starts at
# _end = 0x789D00 and runs to the top of RAM; libkernel's break pointer lives at
# BRK_PTR and sbrk walks it upward from there. EVERY address above 0x789D00 is
# therefore heap - the allocator will eventually hand it out. That is what broke
# the cave at 0x1600070: five save states show the break at 0xCCC000..0xF73000
# (below the cave, everything fine) or at 0x1652000/0x171F000 (past the cave,
# renderer overwritten with texture data -> hooks jump into garbage -> host
# crash on one machine, freeze on another). Intermittent because it depends on
# how far that battle's allocations pushed the break.
#
# So we move the heap base up instead and put the cave in the gap below it:
#   BSS zeroing stops at 0x789D00 (crt0 loop bound, unchanged)
#   overlay PT_LOAD reservations top out at 0x789D00 (max vaddr+memsz)
#   the heap now starts at HEAP_BASE
# which leaves [0x789D00, HEAP_BASE) reachable by nothing at all.
CAVE      = 0x78A070   # in that gap; 6320B cave ends 0x78B920. The low 0x70 is
                       # forced: a PT_LOAD needs foff % 0x80 == vaddr % 0x80 and
                       # the cave is mapped from file offset 0x34D770.
HEAP_BASE = 0x78CD00   # was _end (0x789D00). SHIFT MUST BE A MULTIPLE OF
                       # 0x1000: this moves every heap allocation, and the
                       # original base is 0x789D00, i.e. 0xD00 into its page.
                       # 0x790000 looked tidier but shifted everything by
                       # 0x6300 = 6 pages + 0x300, knocking every allocation
                       # out of its original page alignment - buffers that need
                       # page-aligned memory (texture/portrait loads) then fail,
                       # which showed up as a chapter-2 scene transition that
                       # stalled with an empty box and no portrait (v1.29-v1.40;
                       # v1.25 was clean). 0x78CD00 keeps the same 0xD00 page
                       # offset and shifts by exactly 0x3000 = 3 pages.
BRK_PTR   = 0x3F3FB4   # libkernel break pointer (initialised to _end in .data,
                       # sits right after the "PsIIlibkernl3100" banner)
INITHEAP  = 0x1001D8   # addiu $a0,$a0,-0x6300 -> the InitHeap base argument

# Earlier attempts, kept so they are not retried:
_OLD_CAVE = 0x121810   # held live functions the MALE route calls (hung on
                       # character select; the female route never calls them).
                       # 0x188470: original tail-calls it (j at 0x187A00,
                       # scenario engine) - soft-locked scene events.
                       # 0x3F575C: looks like free padding, but it is live data
                       # the code references 510x, so the cave got overwritten.
                       # 0x1600070: own PT_LOAD, but inside the sbrk heap - see
                       # above. A static "no references" check cannot see this;
                       # only the break pointer can.

# ---- register numbers ----
R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


# ---- tiny MIPS assembler (subset) ----
class Asm:
    def __init__(self, base):
        self.base = base
        self.ins = []      # list of (kind, ...) tuples, resolved in pass 2
        self.labels = {}

    def _emit(self, fn):
        self.ins.append(fn)

    def label(self, name):
        self.labels[name] = self.base + len(self.ins) * 4

    def cur(self):
        return self.base + len(self.ins) * 4

    # R-type
    def _r(self, rs, rt, rd, sa, funct):
        self._emit(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | funct)
    def addu(self, rd, rs, rt): self._r(rs, rt, rd, 0, 0x21)
    def subu(self, rd, rs, rt): self._r(rs, rt, rd, 0, 0x23)
    def sllv(self, rd, rt, rs): self._r(rs, rt, rd, 0, 0x04)
    def sll(self, rd, rt, sa):  self._r('zero', rt, rd, sa, 0x00)
    def jr(self, rs):           self._r(rs, 'zero', 'zero', 0, 0x08)
    def move(self, rd, rs):     self.addu(rd, rs, 'zero')
    def nop(self):              self.sll('zero', 'zero', 0)

    # I-type
    def _i(self, op, rs, rt, imm):
        self._emit(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, rt, rs, imm): self._i(0x09, rs, rt, imm)
    def ori(self, rt, rs, imm):   self._i(0x0D, rs, rt, imm)
    def andi(self, rt, rs, imm):  self._i(0x0C, rs, rt, imm)
    def sltiu(self, rt, rs, imm): self._i(0x0B, rs, rt, imm)
    def lui(self, rt, imm):       self._i(0x0F, 'zero', rt, imm)
    def lbu(self, rt, off, rs):   self._i(0x24, rs, rt, off)
    def sb(self, rt, off, rs):    self._i(0x28, rs, rt, off)
    def lw(self, rt, off, rs):    self._i(0x23, rs, rt, off)
    def sw(self, rt, off, rs):    self._i(0x2B, rs, rt, off)
    def li(self, rt, imm):        self.addiu(rt, 'zero', imm)

    def la(self, rt, addr):       # load absolute address (2 instr)
        self.lui(rt, (addr >> 16) & 0xFFFF)
        self.ori(rt, rt, addr & 0xFFFF)

    # branches (label resolved in pass 2)
    def _b(self, op, rs, rt, lbl):
        idx = len(self.ins)
        def f(_idx=idx, _op=op, _rs=rs, _rt=rt, _lbl=lbl):
            target = self.labels[_lbl]
            pc = self.base + _idx * 4
            off = (target - (pc + 4)) >> 2
            return (_op << 26) | (R[_rs] << 21) | (R[_rt] << 16) | (off & 0xFFFF)
        self._emit(f)
    def beq(self, rs, rt, lbl): self._b(0x04, rs, rt, lbl)
    def bne(self, rs, rt, lbl): self._b(0x05, rs, rt, lbl)
    def beqz(self, rs, lbl):    self.beq(rs, 'zero', lbl)
    def bnez(self, rs, lbl):    self.bne(rs, 'zero', lbl)

    # jumps to absolute targets
    def j(self, addr):   self._emit(lambda: (0x02 << 26) | ((addr >> 2) & 0x03FFFFFF))
    def jal(self, addr): self._emit(lambda: (0x03 << 26) | ((addr >> 2) & 0x03FFFFFF))

    def jlbl(self, lbl):  # jump to a label (resolved in pass 2)
        self._emit(lambda _l=lbl: (0x02 << 26) | ((self.labels[_l] >> 2) & 0x03FFFFFF))

    def assemble(self):
        return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def voff(data, vaddr):
    """File offset for a vaddr, resolved through the ELF's PT_LOAD table (so a
    cave living in its own appended segment works exactly like one inside the
    main image)."""
    phoff = struct.unpack_from("<I", data, 28)[0]
    phnum = struct.unpack_from("<H", data, 44)[0]
    ent = struct.unpack_from("<H", data, 42)[0]
    for k in range(phnum):
        t, o, va, pa, fsz, msz, fl, al = struct.unpack_from("<8I", data, phoff + k*ent)
        if t == 1 and fsz and va <= vaddr < va + fsz:
            return o + (vaddr - va)
    raise KeyError("vaddr %#x is not in any PT_LOAD" % vaddr)


def map_existing(data, foff, size, vaddr):
    """Add a PT_LOAD mapping `size` bytes of file data at `foff` to `vaddr`,
    without growing the file.

    Matches the executable's own conventions, which a strict loader cares about:
      * p_offset/p_vaddr congruent mod p_align (0x80, as every other segment)
      * segment file offsets stay MONOTONIC (the original's are)
      * the final segment (filesz 0, memsz 0, align 0x10) is an end marker, so
        the new entry is INSERTED before it rather than appended after.
    Appending after that marker with a backwards file offset is what stopped the
    game from booting.
    """
    phoff = struct.unpack_from("<I", data, 28)[0]
    phnum = struct.unpack_from("<H", data, 44)[0]
    ent = struct.unpack_from("<H", data, 42)[0]
    assert (foff % 0x80) == (vaddr % 0x80), \
        "align: foff%%0x80=%#x vaddr%%0x80=%#x" % (foff % 0x80, vaddr % 0x80)
    idx = phnum - 1                      # before the end marker
    tbl_end = phoff + (phnum + 1) * ent
    assert tbl_end <= FOFF, "no room for another program header"
    # shift the marker (and anything at/after idx) up one slot
    src = phoff + idx * ent
    data[src + ent:tbl_end] = data[src:tbl_end - ent]
    struct.pack_into("<8I", data, src, 1, foff, vaddr, vaddr, size, size, 7, 0x80)
    struct.pack_into("<H", data, 44, phnum + 1)
    # keep p_offset non-decreasing: any trailing zero-filesz entries (the end
    # marker) still point below us. They read no data, so moving their offset
    # up is free and keeps the table in the shape the loader expects.
    for k in range(idx + 1, phnum + 1):
        p = phoff + k * ent
        t2, o2, va2, pa2, fsz2, msz2, fl2, al2 = struct.unpack_from("<8I", data, p)
        if fsz2 == 0 and o2 < foff + size:
            struct.pack_into("<I", data, p + 4, foff + size)
    # the section table is what we just claimed as cave storage; drop it so
    # nothing tries to read it back
    struct.pack_into("<I", data, 0x20, 0)     # e_shoff
    struct.pack_into("<H", data, 0x30, 0)     # e_shnum
    struct.pack_into("<H", data, 0x32, 0)     # e_shstrndx
    print("  new PT_LOAD @idx %d: vaddr %#x size %d <- file off %#x (was section hdrs)"
          % (idx, vaddr, size, foff))


def add_ptload(data, blob, vaddr):
    """Append blob as a NEW PT_LOAD mapped at vaddr. Exactly one spare program
    header fits before the first segment's file offset."""
    phoff = struct.unpack_from("<I", data, 28)[0]
    phnum = struct.unpack_from("<H", data, 44)[0]
    ent = struct.unpack_from("<H", data, 42)[0]
    while len(data) % 0x80:
        data.append(0)
    foff = len(data)
    assert (foff % 0x80) == (vaddr % 0x80), "segment alignment"
    data += blob
    ph_new = phoff + phnum * ent
    assert ph_new + ent <= FOFF, "no room for another program header"
    struct.pack_into("<8I", data, ph_new, 1, foff, vaddr, vaddr,
                     len(blob), len(blob), 7, 0x80)
    struct.pack_into("<H", data, 44, phnum + 1)
    print("  new PT_LOAD: vaddr %#x  filesz %d  fileoff %#x" % (vaddr, len(blob), foff))
    return foff


def build_table():
    """95 entries for ASCII 0x20..0x7E -> 2-byte fullwidth SJIS (big-endian
    lead,trail). 0x22 and 0x27 remapped into the renderable 0x81 bank."""
    override = {0x22: 0x8168, 0x27: 0x8166}  # " -> ” , ' -> ’
    out = bytearray()
    for c in range(0x20, 0x7F):
        if c in override:
            code = override[c]
        else:
            u = "　" if c == 0x20 else chr(0xFF00 + (c - 0x20))
            b = u.encode("cp932")
            assert len(b) == 2, (hex(c), b)
            code = (b[0] << 8) | b[1]
        lead = (code >> 8) & 0xFF
        assert 0x81 <= lead <= 0x88, (hex(c), hex(code))
        out += bytes([lead, code & 0xFF])
    return bytes(out)


def build_cave():
    # Scratch buffer lives on the stack at sp+SCROFF (no cave data needed).
    FRAME = 0x420
    SCROFF = 0x08            # SCR = sp+0x08 .. sp+0x408  (0x400 bytes)
    a = Asm(CAVE)
    global TBL

    # save frame
    a.addiu('sp', 'sp', -FRAME)
    a.sw('ra', FRAME - 0x04, 'sp')
    a.sw('s0', FRAME - 0x08, 'sp')
    a.sw('s1', FRAME - 0x0C, 'sp')
    a.move('s0', 'a0')       # s0 = this
    a.move('s1', 'a1')       # s1 = src

    a.bnez('s1', 'have_src')
    a.nop()
    a.sb('zero', 0x0C, 's0')  # src==0 -> clear text
    a.jlbl('ret')
    a.nop()

    a.label('have_src')
    a.jal(NEEDEXP)            # v0 = ctx
    a.nop()
    a.beqz('v0', 'plaincopy')
    a.nop()
    # expand(a0=ctx, a1=&SCR, a2=src)
    a.move('a0', 'v0')
    a.addiu('a1', 'sp', SCROFF)
    a.jal(EXPAND)
    a.move('a2', 's1')        # delay slot: set a2 before EXPAND runs
    a.jlbl('convert')
    a.nop()

    a.label('plaincopy')
    a.addiu('a0', 'sp', SCROFF)  # strcpy(&SCR, src)
    a.jal(STRCPY)
    a.move('a1', 's1')        # delay slot

    # -------- convert SCR -> this+0xC --------
    a.label('convert')
    a.addiu('t0', 'sp', SCROFF)  # p = &SCR
    a.addiu('t1', 's0', 0x0C)    # d = this + 0xC
    a.la('t9', TBL)              # TBL (constant, in cave)

    a.label('cv_loop')
    a.lbu('t2', 0, 't0')      # b = *p
    a.beqz('t2', 'cv_done')
    a.nop()
    # 2-byte SJIS lead? (0x81..0x9F) or (0xE0..0xFC)
    a.sltiu('t3', 't2', 0x81)         # t3 = b < 0x81
    a.bnez('t3', 'not_lead_hi')
    a.nop()
    a.sltiu('t3', 't2', 0xA0)         # b < 0xA0  => 0x81..0x9F  (2-byte lead)
    a.bnez('t3', 'copy2')
    a.nop()
    a.sltiu('t3', 't2', 0xE0)         # b < 0xE0  => 0xA0..0xDF  (single byte)
    a.bnez('t3', 'copy1')
    a.nop()
    a.sltiu('t3', 't2', 0xFD)         # b < 0xFD  => 0xE0..0xFC  (2-byte lead)
    a.bnez('t3', 'copy2')
    a.nop()
    a.jlbl('copy1')                   # >=0xFD -> passthrough
    a.nop()

    a.label('not_lead_hi')            # b < 0x81
    a.li('t3', 0x0A)
    a.beq('t2', 't3', 'copy1')        # newline -> passthrough
    a.nop()
    a.sltiu('t3', 't2', 0x20)         # b < 0x20 -> other control, passthrough
    a.bnez('t3', 'copy1')
    a.nop()
    a.sltiu('t3', 't2', 0x7F)         # b <= 0x7E -> printable ASCII
    a.beqz('t3', 'copy1')             # 0x7F -> passthrough
    a.nop()
    # fullwidth: idx=(b-0x20)*2 ; load table entry
    a.addiu('t4', 't2', -0x20)
    a.sll('t4', 't4', 1)
    a.addu('t4', 't9', 't4')
    a.lbu('t5', 0, 't4')              # lead
    a.lbu('t6', 1, 't4')             # trail
    a.sb('t5', 0, 't1')
    a.sb('t6', 1, 't1')
    a.addiu('t1', 't1', 2)
    a.addiu('t0', 't0', 1)
    a.jlbl('cv_loop')
    a.nop()

    a.label('copy2')
    a.sb('t2', 0, 't1')
    a.lbu('t3', 1, 't0')
    a.sb('t3', 1, 't1')
    a.addiu('t1', 't1', 2)
    a.addiu('t0', 't0', 2)
    a.jlbl('cv_loop')
    a.nop()

    a.label('copy1')
    a.sb('t2', 0, 't1')
    a.addiu('t1', 't1', 1)
    a.addiu('t0', 't0', 1)
    a.jlbl('cv_loop')
    a.nop()

    a.label('cv_done')
    a.sb('zero', 0, 't1')             # terminator

    a.label('ret')
    a.lw('ra', FRAME - 0x04, 'sp')
    a.lw('s0', FRAME - 0x08, 'sp')
    a.lw('s1', FRAME - 0x0C, 'sp')
    a.jr('ra')
    a.addiu('sp', 'sp', FRAME)        # delay slot
    return a


def move_heap_base(data):
    """Start the kernel heap at HEAP_BASE instead of _end, so the cave below it
    is outside the heap entirely.

    Two places carry the base and both must agree, or sbrk hands out memory the
    kernel does not own:
      INITHEAP  the addiu supplying arg0 of syscall 0x3D (InitHeap) in crt0
      BRK_PTR   libkernel's break pointer, initialised to _end in .data
    Only the addiu immediate changes; `lui $a0,0x79` already gives 0x790000, so
    the immediate simply drops to 0.
    """
    off = voff(data, INITHEAP)
    w = struct.unpack_from("<I", data, off)[0]
    assert w == 0x24849D00, "InitHeap arg is 0x%08X, not the expected addiu" % w
    imm = HEAP_BASE - 0x790000            # lui $a0,0x79 supplies the high half
    assert -0x8000 <= imm < 0x8000, "heap base too far from 0x790000"
    struct.pack_into("<I", data, off, (w & 0xFFFF0000) | (imm & 0xFFFF))

    off = voff(data, BRK_PTR)
    old = struct.unpack_from("<I", data, off)[0]
    assert old == 0x00789D00, "break pointer is 0x%08X, not _end" % old
    struct.pack_into("<I", data, off, HEAP_BASE)

    assert CAVE >= 0x789D00, "cave below the BSS-zero / overlay-reserve ceiling"
    assert CAVE + 0x18B0 <= HEAP_BASE, "cave overlaps the heap"
    print("  heap base %#010x -> %#010x  (InitHeap arg + break ptr %#x)"
          % (0x789D00, HEAP_BASE, BRK_PTR))
    print("  cave gap  %#010x..%#010x  (%d bytes, cave uses %d)"
          % (0x789D00, HEAP_BASE, HEAP_BASE - 0x789D00, 0x18B0))


def main():
    src_elf, dst_elf = sys.argv[1], sys.argv[2]
    data = bytearray(open(src_elf, "rb").read())

    global TBL
    CAVE_SIZE = 0x660        # size of the dead function at CAVE
    # pass 1: size the code with a dummy TBL addr
    TBL = CAVE + 0x400
    code_len = len(build_cave().ins) * 4
    # place TBL right after code (align 4)
    TBL = (CAVE + code_len + 3) & ~3
    # pass 2: rebuild with real addr; labels now resolve to final positions
    a = build_cave()
    code = a.assemble()
    assert len(code) == code_len

    table = build_table()
    assert TBL + len(table) <= CAVE + CAVE_SIZE, "cave overflow (code+table)"

    CAVE_TOTAL = 0x18B0      # renderer+hooks (0x530) then the font atlas
    if not (VBASE <= CAVE < VBASE + 0x34BC80):
        # The ELF cannot grow (its size on disc is fixed), so instead of
        # appending we point the new segment at file bytes that are ALREADY in
        # the image: the 6988B zero run at 0x3F575C. Those bytes end up mapped
        # twice - once at 0x3F575C (the game's own page, which it overwrites at
        # runtime; that is precisely why the cave failed when it LIVED there)
        # and once at CAVE, which nothing else touches. Our copy is the one the
        # hooks use, so the game trampling the other copy is harmless.
        map_existing(data, 0x34D770, CAVE_TOTAL, CAVE)

    # CAVE only stays untouchable if the heap is moved off it
    move_heap_base(data)

    def put(vaddr, blob):
        foff = voff(data, vaddr)
        data[foff:foff + len(blob)] = blob

    put(CAVE, code)
    put(TBL, table)

    # hook: overwrite setText entry (2 instrs) with `j CAVE ; nop`
    jw = struct.pack("<I", (0x02 << 26) | ((CAVE >> 2) & 0x03FFFFFF))
    put(SETTEXT, jw + struct.pack("<I", 0))

    open(dst_elf, "wb").write(data)
    print("patched ELF written: %s" % dst_elf)
    print("  cave      %#010x  code=%d bytes (dead fn, %d free)" % (CAVE, code_len, CAVE_SIZE - (TBL + len(table) - CAVE)))
    print("  table     %#010x  (%d bytes)" % (TBL, len(table)))
    print("  scratch   on stack (sp+0x08)")
    print("  hook      setText %#010x -> j %#010x" % (SETTEXT, CAVE))


if __name__ == "__main__":
    main()
