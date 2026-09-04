# -*- coding: utf-8 -*-
"""Glossary-link save-stub for the proportional (VWF) BIZ UDGothic font (0.9.45).

patch_vwf_widths' advance table can't live at its old 0x78C110 (that's the spirit
band's blank-cell source) and there's no free cave space, so it moved to 0x78B960
- the UNDERLINE STUB's slot. That stub did copy + save-term-end-X + draw-underline;
we don't want underlines with this font anyway, so this replaces it with a MINIMAL
save-only stub in the freed underscore-constant space (0x78BA10):

    lui at,0x47 ; lh t1,-0x1CC0(at)   ; t1 = term end-X (0x46E340)
    lui t3,0x78 ; ori t3,t3,0xBA50 ; sh t1,0(t3)   ; save to scratch
    jr ra ; nop                       ; return, NO underline copy

The RESTORE stub (0x78B9E0) is left intact and re-hooked, so patch_linkpos still
places post-link text at the term's end (positioning correct). No underscore is
drawn. COPY_FN's return (v0) is unused before it's overwritten at 0x22160C, so
skipping the copy is safe.

Run AFTER: set_atlas <hwatlas_bizud_floor6.bin>, patch_vwf_widths (TABLE_VA
0x78B960), floor_advance_table 6. Idempotent.

Usage: patch_font_linkstub.py <iso> [--write]
"""
import struct
import sys

ELF_LBA, ELF_SIZE = 455, 3471624
def e(va): return 0x1A80 + (va - 0x100000)          # main .text segment
def c(va): return 0x34D770 + (va - 0x78A070)        # cave segment

STUB_VA = 0x78BA10
RESTORE_VA = 0x78B9E0
SAVE_STUB = [0x3C010047, 0x8429E340, 0x3C0B0078, 0x356BBA50, 0xA5690000,
             0x03E00008, 0x00000000]                 # save end-X, jr ra, nop
jal = lambda t: (3 << 26) | ((t >> 2) & 0x3FFFFFF)
# (addr, new instruction, accepted current values)
HOOKS = [
    (0x2215F4, jal(STUB_VA),     (0x0C1E2E58, jal(STUB_VA))),   # copy call -> save stub
    (0x221628, jal(RESTORE_VA),  (0x0C1E2E78, jal(RESTORE_VA))),# -> restore stub
    (0x22162C, 0x00000000,       (0x00000000,)),                # nop (linkpos owns position)
]


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(ELF_LBA * 2048)
    d = bytearray(f.read(ELF_SIZE))
    # sanity: RESTORE stub present, advance table present at 0x78B960
    assert struct.unpack_from("<I", d, c(RESTORE_VA))[0] == 0x3C010078, "RESTORE stub missing"
    assert any(d[c(0x78B960):c(0x78B960) + 69]), "advance table not at 0x78B960 - run patch_vwf_widths first"
    for i, w in enumerate(SAVE_STUB):
        if write:
            struct.pack_into("<I", d, c(STUB_VA) + i * 4, w)
    for va, new, ok in HOOKS:
        cur = struct.unpack_from("<I", d, e(va))[0]
        assert cur in ok, "unexpected %#010x at %#x" % (cur, va)
        if write:
            struct.pack_into("<I", d, e(va), new)
    # verify the spirit-band blank cell is untouched (all zeros)
    assert not any(d[c(0x78C110):c(0x78C110) + 72]), "blank cell 0x78C110 not zero"
    print("save-stub %#x installed; hooks set; blank cell intact; no underline"
          % STUB_VA)
    if write:
        f.seek(ELF_LBA * 2048)
        f.write(bytes(d))
        print("written")
    else:
        print("(dry run)")
    f.close()


main()
