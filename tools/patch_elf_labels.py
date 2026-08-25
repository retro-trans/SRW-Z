# -*- coding: utf-8 -*-
"""Shorten fixed ELF UI labels that collide with the value next to them.

In-place only: each replacement is written into the original string's own
run of bytes (string + its NUL padding), so nothing downstream shifts.
Digits stay FULL-WIDTH - 0x2E..0x3D are control bytes to this renderer,
so an ASCII '1' would be eaten.  Entries carry both the original and the
patched bytes, which makes the tool idempotent and re-runnable on any ELF
generation.

Usage: patch_elf_labels.py <iso> [--revert]
"""
import sys

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80

# (va, original bytes, replacement) - weapon screen, 0x443B60 label table.
# "Effect １" ran into the effect name itself; "Eff１" is ~half the width.
LABELS = [
    (0x443BA8, bytes.fromhex("456666656374208250"), bytes.fromhex("4566668250")),
    (0x443BB8, bytes.fromhex("456666656374208251"), bytes.fromhex("4566668251")),
    # terrain-effect panel: "HP Regen"/"EN Regen" ran into their own +-0%
    # value.  BOTH copies of each - this ELF keeps a separate label table
    # per screen (0x4421A0 and 0x4444B8).
    (0x4421A0, b"HP Regen", b"HP Reg"),
    (0x4421B0, b"EN Regen", b"EN Reg"),
    (0x4444B8, b"HP Regen", b"HP Reg"),
    (0x4444C8, b"EN Regen", b"EN Reg"),
    # level-up / pilot skill panel: names longer than ~12 chars run past the
    # box (user screenshot: "Focused Attack"). Match the abbreviations already
    # used elsewhere - "Chain Atk", "Support Atk", "Ignore Size".
    (0x434918, b"Will Limit Break", b"Will Cap Up"),
    (0x434A28, b"Assist Attack", b"Assist Atk"),
    (0x434A90, b"Focused Attack", b"Focus Atk"),
    (0x434B30, b"Ignore Size Diff", b"Ignore Size"),
]


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    iso = open(iso_path, "r+b")
    for va, old, new in LABELS:
        off = ELF_LBA * SECTOR + (va - VBASE + FOFF)
        iso.seek(off)
        cur = iso.read(len(old))
        want, other = (old, new) if revert else (new, old)
        if cur.startswith(want) and cur[len(want):] == b"\x00" * (len(old) - len(want)):
            print("%#x already %r" % (va, want))
            continue
        assert cur == other, "%#x holds %r, expected %r" % (va, cur, other)
        iso.seek(off)
        iso.write(want + b"\x00" * (len(old) - len(want)))
        print("%#x %r -> %r" % (va, other, want))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
