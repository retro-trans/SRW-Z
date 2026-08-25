"""Custom font injection - STEP 1: PT_LOAD blob + GIF-DMA upload (no redirect yet).

Adds a PT_LOAD mapping [upload packet + flag + code] to vaddr 0x1400000 (free EE
RAM). Repoints setText (0x20C9B0) to a trampoline that, once, DMA-uploads a
256x64 PSMCT32 atlas to VRAM (DBP 0x3800) then jumps to the renderer cave
(0x188470). Verify: after boot, 0x1400000 holds our packet; game runs (no crash).

Blob layout (all 16-aligned):
  +0x00000  upload_packet (GIF host->local)   QWC = len/16
  +PKT_END  flag (4 bytes) + pad
  +CODE     code (upload + trampoline)
"""
import sys, struct

VBASE, FOFF = 0x100000, 0x1A80
BLOB_VA = 0x1400000
ATLAS_W, ATLAS_H = 256, 64
VRAM_DBP = 0x3800
ATLAS_TBW = ATLAS_W // 64
SETTEXT = 0x20C9B0
RENDERER_CAVE = 0x188470

R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
    "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


class Asm:
    def __init__(self, base): self.base = base; self.ins = []; self.labels = {}
    def label(self, n): self.labels[n] = self.base + len(self.ins) * 4
    def _e(self, f): self.ins.append(f)
    def _r(self, rs, rt, rd, sa, fn): self._e(lambda: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)
    def and_(self, d, s, t): self._r(s, t, d, 0, 0x24)
    def jr(self, s): self._r(s, 'zero', 'zero', 0, 8)
    def nop(self): self._r('zero', 'zero', 'zero', 0, 0)
    def _i(self, op, rs, rt, imm): self._e(lambda: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))
    def addiu(self, t, s, i): self._i(0x09, s, t, i)
    def andi(self, t, s, i): self._i(0x0C, s, t, i)
    def ori(self, t, s, i): self._i(0x0D, s, t, i)
    def lui(self, t, i): self._i(0x0F, 'zero', t, i)
    def lw(self, t, o, s): self._i(0x23, s, t, o)
    def sw(self, t, o, s): self._i(0x2B, s, t, o)
    def li(self, t, i): self.addiu(t, 'zero', i)
    def la(self, t, a): self.lui(t, (a >> 16) & 0xFFFF); self.ori(t, t, a & 0xFFFF)
    def _b(self, op, rs, rt, lbl):
        idx = len(self.ins)
        def f(_i=idx, _op=op, _rs=rs, _rt=rt, _l=lbl):
            off = (self.labels[_l] - (self.base + _i * 4 + 4)) >> 2
            return (_op << 26) | (R[_rs] << 21) | (R[_rt] << 16) | (off & 0xFFFF)
        self._e(f)
    def beqz(self, s, l): self._b(4, s, 'zero', l)
    def bnez(self, s, l): self._b(5, s, 'zero', l)
    def j(self, a): self._e(lambda: (2 << 26) | ((a >> 2) & 0x03FFFFFF))
    def jal(self, a): self._e(lambda: (3 << 26) | ((a >> 2) & 0x03FFFFFF))
    def bytes_(self): return b"".join(struct.pack("<I", f() & 0xFFFFFFFF) for f in self.ins)


def qw(lo, hi=0): return struct.pack("<QQ", lo & (2**64 - 1), hi & (2**64 - 1))


def build_packet(atlas):
    img_qwc = len(atlas) // 16
    p = qw((1 << 60) | (1 << 15) | 4, 0xE)                       # GIFtag A+D, NLOOP=4
    p += qw((VRAM_DBP << 32) | (ATLAS_TBW << 48) | (0 << 56), 0x50)  # BITBLTBUF
    p += qw(0, 0x51)                                             # TRXPOS
    p += qw((ATLAS_H << 32) | ATLAS_W, 0x52)                    # TRXREG
    p += qw(0, 0x53)                                            # TRXDIR host->local
    p += qw((2 << 58) | (1 << 15) | img_qwc, 0)                 # GIFtag IMAGE
    p += atlas
    return p


def main():
    src, dst, atlas_bin = sys.argv[1], sys.argv[2], sys.argv[3]
    data = bytearray(open(src, "rb").read())
    atlas = open(atlas_bin, "rb").read()
    assert len(atlas) == ATLAS_W * ATLAS_H * 4

    packet = build_packet(atlas)
    QWC = len(packet) // 16
    PKT_VA = BLOB_VA
    FLAG_VA = PKT_VA + ((len(packet) + 15) & ~15)
    CODE_VA = FLAG_VA + 16

    a = Asm(CODE_VA)
    a.label('upload')                       # (== CODE_VA)
    a.la('t0', FLAG_VA); a.lw('t1', 0, 't0')
    a.bnez('t1', 'u_done'); a.nop()
    a.li('t1', 1); a.sw('t1', 0, 't0')
    a.lui('at', 0x1001)
    a.la('t0', PKT_VA)
    a.lui('t1', 0x0FFF); a.ori('t1', 't1', 0xFFFF); a.and_('t0', 't0', 't1')  # phys
    a.sw('t0', -0x5FF0, 'at')               # D2_MADR
    a.li('t0', QWC); a.sw('t0', -0x5FE0, 'at')      # D2_QWC
    a.li('t0', 0x101); a.sw('t0', -0x6000, 'at')    # D2_CHCR
    a.label('u_wait')
    a.lw('t0', -0x6000, 'at'); a.andi('t0', 't0', 0x100)
    a.bnez('t0', 'u_wait'); a.nop()
    a.label('u_done')
    a.jr('ra'); a.nop()

    a.label('tramp')
    a.addiu('sp', 'sp', -0x10); a.sw('ra', 0, 'sp')
    a.jal(CODE_VA); a.nop()                 # jal upload
    a.lw('ra', 0, 'sp'); a.addiu('sp', 'sp', 0x10)
    a.j(RENDERER_CAVE); a.nop()
    code = a.bytes_()
    tramp_va = a.labels['tramp']

    blob = bytearray(packet)
    while len(blob) % 16: blob.append(0)
    assert BLOB_VA + len(blob) == FLAG_VA
    blob += b"\x00" * 16                     # flag(4) + pad to CODE_VA
    assert BLOB_VA + len(blob) == CODE_VA
    blob += code

    # ELF surgery
    e_phoff = struct.unpack('<I', data[28:32])[0]
    e_phnum = struct.unpack('<H', data[44:46])[0]
    e_phentsize = struct.unpack('<H', data[42:44])[0]
    # p_offset must be congruent to p_vaddr (mod p_align=0x80). BLOB_VA is 0x80-
    # aligned, so pad the file to a 0x80 boundary before appending the blob.
    while len(data) % 0x80:
        data.append(0)
    blob_foff = len(data)
    assert (blob_foff % 0x80) == (BLOB_VA % 0x80), "PT_LOAD offset/vaddr misaligned"
    data += blob
    ph_new = e_phoff + e_phnum * e_phentsize
    assert ph_new + e_phentsize <= FOFF, "no PH room"
    data[ph_new:ph_new + e_phentsize] = struct.pack(
        '<8I', 1, blob_foff, BLOB_VA, BLOB_VA, len(blob), len(blob), 7, 0x80)
    struct.pack_into('<H', data, 44, e_phnum + 1)
    # repoint setText -> tramp
    struct.pack_into('<I', data, FOFF + (SETTEXT - VBASE),
                     (2 << 26) | ((tramp_va >> 2) & 0x03FFFFFF))
    open(dst, "wb").write(data)
    print("STEP1 written:", dst)
    print("  PT_LOAD @%#x size=%#x (foff %#x)" % (BLOB_VA, len(blob), blob_foff))
    print("  PKT_VA=%#x QWC=%d FLAG=%#x CODE=%#x tramp=%#x" % (PKT_VA, QWC, FLAG_VA, CODE_VA, tramp_va))
    print("  setText %#x -> j tramp" % SETTEXT)


if __name__ == "__main__":
    main()
