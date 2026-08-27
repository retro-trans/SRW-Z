# -*- coding: utf-8 -*-
"""Simulate the v2 advance trampoline before writing it.

Entry: t0 = glyph code. Exit: v1 = pen advance for that glyph, then the hook
does `addu v1,a0,v1` at 0x78BAB0. Branch target is idx+1+imm (PC+4 + imm*4).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_vwf_widths as P

NAME = {0: "zero", 1: "at", 3: "v1", 8: "t0"}


def sim(code, tbl, glyph_code):
    r = {"zero": 0, "at": 0, "v1": 0, "t0": glyph_code}
    def g(i): return 0 if i == 0 else r.get(NAME.get(i, "?"), 0)
    def sx(v): return v - 0x10000 if v & 0x8000 else v
    def run(x):
        op = x >> 26; rs = (x >> 21) & 31; rt = (x >> 16) & 31
        rd = (x >> 11) & 31; im = x & 0xFFFF; fn = x & 0x3F
        if x == 0: return
        if op == 0x0D: r[NAME[rt]] = g(rs) | im
        elif op == 0x0B: r[NAME[rt]] = 1 if g(rs) < im else 0
        elif op == 0x09: r[NAME[rt]] = (g(rs) + sx(im)) & 0xFFFFFFFF
        elif op == 0x0F: r[NAME[rt]] = (im << 16)
        elif op == 0x24:
            idx = ((g(rs) + sx(im)) & 0xFFFFFFFF) - P.TABLE_VA
            if not (0 <= idx < len(tbl)):
                raise AssertionError("table read out of range: %d" % idx)
            r[NAME[rt]] = tbl[idx]
        elif op == 0 and fn == 0x21: r[NAME[rd]] = (g(rs) + g(rt)) & 0xFFFFFFFF
        elif op == 0 and fn == 0x23: r[NAME[rd]] = (g(rs) - g(rt)) & 0xFFFFFFFF
        else: raise AssertionError("unhandled op %#x (%08X)" % (op, x))
    pc, steps = 0, 0
    while 0 <= pc < len(code) and steps < 50:
        steps += 1
        x = code[pc]; op = x >> 26
        if op == 0x05:
            rs = (x >> 21) & 31; rt = (x >> 16) & 31; im = x & 0xFFFF
            taken = g(rs) != g(rt)
            run(code[pc + 1])
            pc = pc + 1 + (im - 0x10000 if im & 0x8000 else im) if taken else pc + 2
            continue
        if op == 0x02:
            run(code[pc + 1]); break
        run(x); pc += 1
    return r["v1"]


def main():
    f = open(sys.argv[1], "rb"); f.seek(455 * 2048)
    elf = bytearray(f.read(P.ELF_SIZE)); f.close()
    tbl = P.measure(elf)
    code = P.build_tramp()
    CH = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A)) + \
         list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
    bad = 0
    for idx in range(138):
        got = sim(code, tbl, 0x8540 + idx)
        want = tbl[idx] + 1 if idx < 69 else tbl[idx - 69] + 2
        if got != want:
            bad += 1
            if bad <= 6:
                print("MISMATCH idx %3d: got %d want %d" % (idx, got, want))
        if got > 13:
            bad += 1
            print("OVER 13 at idx %d: %d - a line could get WIDER" % (idx, got))
    print("simulated 138 indices: %s" % ("ALL CORRECT" if not bad else "%d WRONG" % bad))
    print("max advance %d (must be <= 13 so no line can widen)"
          % max(sim(code, tbl, 0x8540 + i) for i in range(138)))
    for idx in (0, 25, 51, 54, 68, 69, 123):
        print("   %r%s -> advance %d"
              % (chr(CH[idx % 69]), " bold" if idx >= 69 else "     ",
                 sim(code, tbl, 0x8540 + idx)))


if __name__ == "__main__":
    main()
