# -*- coding: utf-8 -*-
"""Restore ORIGINAL bytes for selected ELF_UI string slots in a patched ELF.
Used to bisect which UI string replacement breaks the game.

Usage:
  revert_elfui.py <in.elf> <out.elf> ctrl              # only control-code slots
  revert_elfui.py <in.elf> <out.elf> grew              # only slots whose English grew
  revert_elfui.py <in.elf> <out.elf> range <lo> <hi>   # hex file-offset range
  revert_elfui.py <in.elf> <out.elf> list <o1,o2,...>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elf_ui_en import ELF_UI

ORIG = r"E:\Projects\SRW Z\_work\hwbuild\orig.elf"


def slot(og, off):
    end = og.find(b"\x00", off)
    if end < 0 or end - off > 300:
        return None
    k = end
    while k < len(og) and og[k] == 0 and k - end < 12:
        k += 1
    return end, k


def main():
    src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    og = open(ORIG, "rb").read()
    data = bytearray(open(src, "rb").read())
    assert len(data) == len(og), "size mismatch"

    targets = []
    for off, en in ELF_UI.items():
        s = slot(og, off)
        if s is None:
            continue
        end, k = s
        orig = og[off:end]
        if mode == "ctrl":
            if any(b < 0x20 and b != 0x0A for b in orig):
                targets.append((off, k))
        elif mode == "grew":
            enc = en if isinstance(en, bytes) else en.encode("cp932", "replace")
            if len(enc) > len(orig):
                targets.append((off, k))
        elif mode == "range":
            lo, hi = int(sys.argv[4], 16), int(sys.argv[5], 16)
            if lo <= off < hi:
                targets.append((off, k))
        elif mode == "list":
            if off in {int(x, 16) for x in sys.argv[4].split(",")}:
                targets.append((off, k))
        else:
            raise SystemExit("unknown mode " + mode)

    for off, k in targets:
        data[off:k] = og[off:k]
    open(dst, "wb").write(bytes(data))
    print("reverted %d slots (mode=%s) -> %s" % (len(targets), mode, dst))


if __name__ == "__main__":
    main()
