# -*- coding: utf-8 -*-
"""Battle voice-caption paging fix, v3 (option B done right).

HOW CAPTIONS WORK (established over 0.8.1.2-0.8.1.6):
Two display paths (page-advance fn 0x2EA320 chan=s2, caption-start fn
0x2EA4B0 chan=s3) compute  text = quote_base + OFFSET  and feed it to the
\\n->0x0A converter 0x2EA280, which fills the display buffer. The OFFSET
comes from voice-sync descriptors authored for the JAPANESE text and has
TWO meanings:
  * a FIELD SELECTOR - picks a whole line (attack cry vs hit reaction...)
    out of the pilot's quote block. srvc.build space-pads every English
    field to the original extent, so FIELD STARTS ARE PRESERVED and these
    offsets remain CORRECT for English data.
  * a MID-FIELD PAGE - points just past a \\n inside one utterance. Those
    byte positions shift with translation, which was the original
    head-truncation bug ('"Target approach!\\nFollow me now!"' paged to
    'ach!...').
0.8.1.4/5 ignored the offset entirely and \\n-scanned from the base, which
fixed pages but BROKE field selection: hit reactions showed the attacker's
first line (user report). This version keeps the offset and disambiguates:

CAVE LOGIC (per fill):
  p = base + offset (the ORIGINAL computation, hooks restored)
  scan back from p to the previous NUL -> field_start
  if p == field_start: trust it (field selector)          -> show p
  else: JP mid-field page -> \\n-scan from field_start,
        skipping (channel->curpage - 1) literal "\\n"s,
        falling back to the LAST page when the English
        line has fewer pages (no blank captions)          -> show page

Hooks: only the two jal converter sites are redirected (0x2EA47C -> cave1
s2-variant, 0x2EA684 -> cave2 s3-variant). The two addu s0,a0,v1 sites are
RESTORED to original. Caves at 0x78BBA0/0x78BC40; PT_LOAD fsz -> 0x1CE0.

Usage: patch_caption_paging.py <iso> [--revert]
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80
CAVE_FILE, CAVE_VA = 0x34D770, 0x78A070
OLD_FSZS = (0x1B30, 0x1BA0, 0x1C00, 0x1C80, 0x2198)
NEW_FSZ = 0x1CE0
CAVE = 0x78BBA0
CAVE2 = 0x78BC40
CONVERTER = 0x2EA280

# How far back FINDSTART may walk before it gives up. The scan looks for the
# NUL that ends the PREVIOUS field, so the honest distance is at most one
# field: the longest string in SRVC.BIN is 86 bytes japanese, 94 ours. 256 is
# far past that and still nothing next to a runaway.
#
# WHY THIS EXISTS: the loop used to have no floor at all. When p sits at the
# start of the quote block there is no preceding NUL to find, so the scan walks
# backwards out of the block into whatever precedes it in RAM.
#
#   PCSX2 zero-fills all 32 MB of EE RAM at boot, so the very first byte it
#   reads outside the block is 0 and the scan stops immediately, with
#   field_start == p - the "trust the offset" fast path. It is correct there by
#   accident.
#
#   A real PS2 does not zero RAM. The scan runs on into garbage until it meets
#   a byte that happens to be 0, and returns a field_start pointing at nothing.
#   p != field_start then, so we take the mid-field paging path and hand the
#   converter a pointer into unrelated memory; 0x2EA280 copies from it until a
#   NUL and overruns its fixed caption buffer.
#
# That is a hardware-only crash on the caption-start path - i.e. exactly when a
# battle animation begins - which is what was reported. Reaching the backstop
# now falls back to field_start = p, the same fast path PCSX2 took by luck.
BACKSTOP = 0x100

def f(va): return CAVE_FILE + (va - CAVE_VA)
def e(va): return FOFF + (va - VBASE)


def asm_cave(cave_va, chan_lw):
    """chan_lw: lw t0,0x54(s2)=0x8E480054 or lw t0,0x54(s3)=0x8E680054."""
    w = []
    def at(): return cave_va + len(w) * 4
    labels = {}
    fixups = []
    def br(op, name):
        fixups.append((len(w), op, name)); w.append(None)
    # a1 = p = base+offset (delay slot of the jal passed s0 through)
    w.append(chan_lw)             # lw    t0,0x54(chan)
    w.append(0x00A0C82D)          # daddu t9,a1,zero      p
    w.append(0x00A0C02D)          # daddu t8,a1,zero      field-start scanner
    w.append(0x24090000 | BACKSTOP)   # addiu t1,zero,BACKSTOP
    labels['FINDSTART'] = at()
    w.append(0x930AFFFF)          # lbu   t2,-1(t8)
    br(0x11400000, 'GOTSTART')    # beq   t2,zero,GOTSTART
    w.append(0)                   # nop
    w.append(0x2529FFFF)          # addiu t1,t1,-1
    br(0x1D200000, 'FINDSTART')   # bgtz  t1,FINDSTART
    w.append(0x2718FFFF)          # (delay) addiu t8,t8,-1
    # backstop hit: no field start within reach, so trust the offset instead of
    # a pointer we invented. t8 = p makes GOTSTART's beq fire and take CALL.
    w.append(0x0320C02D)          # daddu t8,t9,zero
    labels['GOTSTART'] = at()
    br(0x13380000, 'CALL')        # beq   t9,t8,CALL      p at field start -> trust
    w.append(0)                   # nop
    # mid-field: page semantics from the field start
    w.append(0x0300C82D)          # daddu t9,t8,zero      p = field start
    w.append(0x2508FFFF)          # addiu t0,t0,-1        skips = curpage-1
    labels['OUTER'] = at()
    br(0x19000000, 'CALL')        # blez  t0,CALL
    w.append(0)                   # nop
    labels['INNER'] = at()
    w.append(0x932A0000)          # lbu   t2,0(t9)
    br(0x11400000, 'LASTPG')      # beq   t2,zero,LASTPG  out of text
    w.append(0)                   # nop
    w.append(0x240B005C)          # addiu t3,zero,0x5C
    br(0x154B0000, 'ADV')         # bne   t2,t3,ADV
    w.append(0)                   # nop
    w.append(0x932A0001)          # lbu   t2,1(t9)
    w.append(0x240B006E)          # addiu t3,zero,0x6E
    br(0x154B0000, 'ADV')         # bne   t2,t3,ADV
    w.append(0)                   # nop
    w.append(0x27390002)          # addiu t9,t9,2         skip the \n
    w.append(0x0320C02D)          # daddu t8,t9,zero      new segment start
    br(0x10000000, 'OUTER')       # b     OUTER
    w.append(0x2508FFFF)          # (delay) addiu t0,t0,-1
    labels['ADV'] = at()
    br(0x10000000, 'INNER')       # b     INNER
    w.append(0x27390001)          # (delay) addiu t9,t9,1
    labels['LASTPG'] = at()
    w.append(0x0300C82D)          # daddu t9,t8,zero      reuse last page
    labels['CALL'] = at()
    w.append(0x0320282D)          # daddu a1,t9,zero
    w.append(0x08000000 | (CONVERTER >> 2))   # j converter
    w.append(0)                   # nop
    for ix, op, name in fixups:
        pc = cave_va + ix * 4 + 4
        w[ix] = op | (((labels[name] - pc) // 4) & 0xFFFF)
    return w


# jal-site hooks; the addu s0,a0,v1 sites must hold the ORIGINAL word
JAL_ORIG = 0x0C000000 | (CONVERTER >> 2)
HOOKS = [
    (0x2EA47C, JAL_ORIG, 0x0C000000 | (CAVE >> 2)),
    (0x2EA684, JAL_ORIG, 0x0C000000 | (CAVE2 >> 2)),
]
ADDU_SITES = [(0x2EA438, 0x00838021), (0x2EA644, 0x00838021)]
NEUTERED = 0x0080802D              # daddu s0,a0,zero (0.8.1.4/5 state)


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    ELF_LBA, SECTOR = 455, 2048
    w1 = asm_cave(CAVE, 0x8E480054)
    w2 = asm_cave(CAVE2, 0x8E680054)
    assert CAVE + len(w1) * 4 <= CAVE2
    assert CAVE2 + len(w2) * 4 <= CAVE_VA + NEW_FSZ
    with open(iso_path, "r+b") as iso:
        base = ELF_LBA * SECTOR
        iso.seek(base + 0x1C)
        e_phoff = struct.unpack("<I", iso.read(4))[0]
        iso.seek(base + 0x2A)
        phent, phnum = struct.unpack("<HH", iso.read(4))
        found = False
        for i in range(phnum):
            o = base + e_phoff + i * phent
            iso.seek(o + 8)
            vaddr = struct.unpack("<I", iso.read(4))[0]
            if vaddr == CAVE_VA:
                iso.seek(o + 16)
                fsz = struct.unpack("<I", iso.read(4))[0]
                assert fsz in OLD_FSZS + (NEW_FSZ,), hex(fsz)
                iso.seek(o + 16)
                # NEVER shrink: grow_cave.py extends this same segment into the
                # ELF's last-sector slack, and later hooks live above NEW_FSZ.
                # Writing NEW_FSZ flat would unload them. Reverting this patch
                # only zeroes the cave bodies; it does not free the segment.
                v = max(fsz, NEW_FSZ)
                iso.write(struct.pack("<II", v, v))
                found = True
        assert found
        # restore the addu sites to ORIGINAL (undo 0.8.1.4/5 neutering)
        for va, orig in ADDU_SITES:
            iso.seek(base + e(va))
            cur = struct.unpack("<I", iso.read(4))[0]
            assert cur in (orig, NEUTERED), hex(cur)
            iso.seek(base + e(va))
            iso.write(struct.pack("<I", orig))
        # cave bodies
        for cva, ws in ((CAVE, w1), (CAVE2, w2)):
            iso.seek(base + f(cva))
            if revert:
                iso.write(b"\x00" * (len(ws) * 4))
            else:
                iso.write(b"".join(struct.pack("<I", x) for x in ws))
        # jal hooks (accept any prior cave address when re-patching)
        for va, orig, new in HOOKS:
            iso.seek(base + e(va))
            cur = struct.unpack("<I", iso.read(4))[0]
            put = orig if revert else new
            assert (cur >> 26) == 0x03, hex(cur)   # must be a jal
            iso.seek(base + e(va))
            iso.write(struct.pack("<I", put))
            print("va %#x: %08x -> %08x" % (va, cur, put))
    print("caption paging v3 %s" % ("reverted" if revert else "patched"))


if __name__ == "__main__":
    main()
