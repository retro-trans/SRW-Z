# -*- coding: utf-8 -*-
"""Repoint the map-command menu labels to FULLWIDTH English strings.

The 22 command labels (cluster 0x441FA8-0x44207C) sit in 4-8 byte slots -
far too small for fullwidth text - and are referenced from code via
lui 0x44 / addiu lo pairs (plus a few data-table words). We write the
fullwidth strings into three NUL padding gaps on the same 64K page
(so every lui stays 0x44) and patch only the addiu immediates / table
words. The original Japanese strings remain in place for any reader we
did not identify.

Usage: patch_cmdmenu.py <in.elf> <out.elf>
"""
import struct
import sys

FOFF, VBASE = 0x1A80, 0x100000

# command string VA -> fullwidth English
CMDS = {
    0x441FA8: ("移動", "Ｍｏｖｅ"),
    0x441FB0: ("搭載", "Ｌｏａｄ"),
    0x441FB8: ("待機", "Ｗａｉｔ"),
    0x441FC0: ("攻撃", "Ａｔｔａｃｋ"),
    0x441FC8: ("空中", "Ａｉｒ"),
    0x441FD0: ("地上", "Ｇｒｏｕｎｄ"),
    0x441FD8: ("水中", "Ｗａｔｅｒ"),
    0x441FE0: ("発進", "Ｌａｕｎｃｈ"),
    0x441FE8: ("修理", "Ｒｅｐａｉｒ"),
    0x441FF0: ("補給", "Ｓｕｐｐｌｙ"),
    0x441FF8: ("変形", "Ｍｏｒｐｈ"),
    0x442000: ("分離", "Ｓｐｌｉｔ"),
    0x442008: ("合体", "Ｃｏｍｂｉｎｅ"),
    0x442010: ("パーツ", "Ｐａｒｔｓ"),
    0x442020: ("フォーメーション", "Ｆｏｒｍａｔｉｏｎ"),
    0x442038: ("精神", "Ｓｐｉｒｉｔ"),
    0x442040: ("能力", "Ｓｔａｔ"),
    0x442048: ("説得", "Ｐｅｒｓｕａｄｅ"),
    0x442050: ("戦術換装", "Ｒｅｆｉｔ"),
    0x442060: ("合神", "Ｕｎｉｔｅ"),
    0x442068: ("トリニティＣ", "ＴｒｉｎｉｔｙＣ"),
    0x442078: ("回収", "Ｒｅｃｏｖｅｒ"),
}

# NUL padding gaps (file offsets) on the lui-0x44 page (va 0x438000-0x447FFF)
GAPS = [(0x33B560, 128), (0x33B660, 128), (0x347CC0, 64),
        # padding freed by shorter EN translations (post-apply_elf; the
        # zero-check below fails loudly if a future edit shifts them)
        (0x33AAA0, 48), (0x33C494, 44), (0x33CC94, 44)]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())

    # sanity: verify each JP string is where we expect (in the ORIGINAL slots
    # apply_elf may already have written ASCII there - accept either)
    for va, (jp, en) in CMDS.items():
        off = va - VBASE + FOFF
        cur = bytes(data[off:off + 20]).split(b"\x00")[0]
        if cur != jp.encode("cp932"):
            print("  note: %#x now %r (translated in-place already)" % (va, cur))

    # verify gaps are zero
    for g, n in GAPS:
        assert all(b == 0 for b in data[g:g + n]), "gap %#x not empty" % g

    # allocate new strings
    alloc = []
    gi, gpos = 0, 0
    newva = {}
    for va in sorted(CMDS):
        enc = CMDS[va][1].encode("cp932") + b"\x00"
        n = len(enc)
        while gi < len(GAPS) and gpos + n > GAPS[gi][1]:
            gi += 1; gpos = 0
        assert gi < len(GAPS), "out of gap space"
        g, _ = GAPS[gi]
        data[g + gpos:g + gpos + len(enc)] = enc
        newva[va] = g + gpos - FOFF + VBASE
        gpos += n
    print("placed %d fullwidth strings" % len(newva))

    # patch ONLY lui/addiu pairs inside the map-command-menu code cluster
    # (0x350800-0x351400). A blanket rewrite of every reference hijacks
    # unrelated consumers: these strings also sit in shared label arrays
    # walked by other screens (the weapon-detail panel bug of 2026-08-13).
    LO, HI = (0x350800 - VBASE + FOFF) // 4, (0x351400 - VBASE + FOFF) // 4
    words = struct.unpack("<%dI" % (len(data) // 4), bytes(data[:len(data) // 4 * 4]))
    patched = 0
    for i in range(LO, HI):
        w = words[i]
        if (w >> 26) == 0x0F and (w & 0xFFFF) == 0x0044:          # lui rt,0x44
            rt = (w >> 16) & 31
            for j in range(i + 1, min(i + 10, len(words))):
                w2 = words[j]
                if (w2 >> 26) == 0x09 and ((w2 >> 21) & 31) == rt:  # addiu x,rt,lo
                    lo = w2 & 0xFFFF
                    va = 0x440000 + (lo - 0x10000 if lo >= 0x8000 else lo)
                    if va in newva:
                        nlo = newva[va] - 0x440000
                        assert -0x8000 <= nlo < 0x8000
                        struct.pack_into("<I", data, j * 4,
                                         (w2 & 0xFFFF0000) | (nlo & 0xFFFF))
                        patched += 1
    open(dst, "wb").write(bytes(data))
    print("patched %d references -> %s" % (patched, dst))


if __name__ == "__main__":
    main()
