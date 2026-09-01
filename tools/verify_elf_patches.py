# -*- coding: utf-8 -*-
"""Assert every ELF patch is present in an ISO. Run BEFORE building a CHD.

Born 2026-08-20: the level-up-spirits word at 0x343630 silently reverted
to the original between the 0.8.1.8 build and the next edit session (cause
unidentified - possibly a lost write while a background build chain held
the file). One missing word costs a full rebuild cycle with the user, so
every build now gets a checklist pass.

Usage: verify_elf_patches.py <iso>     exits nonzero on any mismatch
"""
import struct
import sys

VBASE, FOFF = 0x100000, 0x1A80

CHECKS = [
    # (name, va, expected word)
    ("linkpos lui",          0x22163C, 0x3C010047),
    ("underline hook",       0x2215F4, None),          # jal (opcode check)
    ("backlog conv hook",    0x221430, None),
    ("vlabel SKILL S",       0x443878, None),          # bytes check below
    ("caption addu1 orig",   0x2EA438, 0x00838021),
    ("caption addu2 orig",   0x2EA644, 0x00838021),
    ("caption jal1 cave",    0x2EA47C, 0x0C000000 | (0x78BBA0 >> 2)),
    ("caption jal2 cave2",   0x2EA684, 0x0C000000 | (0x78BC40 >> 2)),
    ("lvlup spirits -30",    0x343630, 0x2447FFE2),
    # 0.9.10: compose_name's flag test is ORIGINAL again. Forcing the branch
    # (0.9.9) fixed Jiron and broke the protagonist - the real fix was the
    # per-record flag in COMPDATA, see fix_name_order_flag.py.
    ("name flag test intact", 0x35F160, 0x14400015),
]
BYTES_CHECKS = [
    ("vlabel SKILL bytes", 0x443878, bytes.fromhex("82720a826a0a8268")),
    ("cave1 head",         0x78BBA0, bytes.fromhex("5400488e")),  # lw t0,0x54(s2) LE
    ("ep prefix 'Ep.'",    0x445DA8, b"Ep.\x00\x00\x00\x00\x00"),
    ("ep suffix empty",    0x445CD8, b"\x00" * 8),
    ("ep fmt 'Ep.%s'",     0x441F50, b"Ep.%s: '%s'\x00"),
    # 0.9.11: the foreign-name separator. Japanese joins a foreign name with a
    # middle dot; english wants a space. Reverting this brings back the dot in
    # "Setsuko Ohara" and "Andrew Waltfeld".
    ("name separator space", 0x442710, bytes([0x25, 0x73, 0x20, 0x25, 0x73, 0, 0])),
]


def main():
    iso_path = sys.argv[1]
    with open(iso_path, "rb") as f:
        f.seek(455 * 2048)
        elf = f.read(3471624)
    def word(va):
        return struct.unpack_from("<I", elf, va - VBASE + FOFF)[0]
    def raw(va, n):
        if va >= 0x78A070:                 # cave segment mapping
            off = 0x34D770 + (va - 0x78A070)
        else:
            off = va - VBASE + FOFF
        return elf[off:off + n]
    bad = 0
    for name, va, want in CHECKS:
        got = word(va)
        if want is None:
            ok = (got >> 26) == 0x03 if "hook" in name else True
        else:
            ok = got == want
        if not ok:
            print("FAIL %-22s %#x = %08X (want %s)"
                  % (name, va, got, "%08X" % want if want else "jal"))
            bad += 1
    for name, va, want in BYTES_CHECKS:
        got = raw(va, len(want))
        if got != want:
            print("FAIL %-22s %#x = %s (want %s)"
                  % (name, va, got.hex(), want.hex()))
            bad += 1
    # cave PT_LOAD size
    e_phoff = struct.unpack_from("<I", elf, 0x1C)[0]
    phent, phnum = struct.unpack_from("<HH", elf, 0x2A)
    for i in range(phnum):
        o = e_phoff + i * phent
        vaddr = struct.unpack_from("<I", elf, o + 8)[0]
        if vaddr == 0x78A070:
            fsz = struct.unpack_from("<I", elf, o + 16)[0]
            if fsz < 0x1CE0:
                print("FAIL cave PT_LOAD fsz = %#x (< 0x1CE0)" % fsz)
                bad += 1
    # every jal/j from the main image into the cave must land on real code:
    # a blanket-zeroed cave range once wiped five stubs and shipped twice
    # (0.8.32/0.8.33 crashed on the load screen).
    seen = set()
    for off in range(FOFF, FOFF + 0x34BC80, 4):
        w = struct.unpack_from("<I", elf, off)[0]
        if (w >> 26) in (2, 3):
            t = (w & 0x3FFFFFF) << 2
            if 0x78A070 <= t < 0x78C208 and t not in seen:
                seen.add(t)
                if struct.unpack_from("<I", elf, 0x34D770 + (t - 0x78A070))[0] == 0:
                    print("FAIL dead cave target %#x (called from %#x)"
                          % (t, 0x100000 + off - FOFF))
                    bad += 1
    if bad:
        print("%d ELF patch check(s) FAILED" % bad)
        sys.exit(1)
    print("all ELF patches present")


if __name__ == "__main__":
    main()
