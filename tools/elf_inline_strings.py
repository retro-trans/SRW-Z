# -*- coding: utf-8 -*-
u"""Recover (and patch) strings that the ELF builds from MIPS immediates.

A handful of UI labels are not stored as text anywhere on the disc. The
compiler inlined them: the routine loads four bytes at a time with a
lui/ori pair and stores them into the display struct with an unaligned
swl/swr pair, so "格闘武器（　　）" exists only as sixteen bytes spread
across eight instruction immediates. No byte search of the disc or of EE
RAM finds them - the only contiguous copy is the one the code writes at
runtime.

This walks a code window basic block by basic block (immediates never
cross a branch), replays the stores into a per-block buffer keyed by base
register, and reports each contiguous run of bytes together with the
address of every instruction that carries part of it.

Patching keeps the instruction layout byte for byte: only the imm16
fields change, so nothing moves and no relocation is needed. That fixes
the budget at the japanese byte length - a replacement is padded with
spaces to exactly that many bytes, and the routine's own terminator stays
where it was.

  elf_inline_strings.py list  <lo> <hi> [iso]
  elf_inline_strings.py patch <iso> <json>     {"<site>": "<english>"}
"""
import json
import struct
import sys

BR = {0x04, 0x05, 0x06, 0x07, 0x14, 0x15, 0x16, 0x17}   # beq/bne/blez/bgtz + likely
STORE = {0x2b: 'sw', 0x2a: 'swl', 0x2e: 'swr'}


def blocks(d, lo):
    u"""Split a code window into basic blocks."""
    bounds = {0, len(d)}
    for i in range(0, len(d) - 4, 4):
        w = struct.unpack_from('<I', d, i)[0]
        op = w >> 26
        if op in BR:
            s = (w & 0xffff)
            s = s - 0x10000 if s & 0x8000 else s
            t = i + 4 + s * 4
            if 0 <= t < len(d):
                bounds.add(t)
            bounds.add(i + 8)
        elif op in (0x02, 0x03) or w == 0x03e00008:
            bounds.add(i + 8)
    b = sorted(bounds)
    return list(zip(b, b[1:]))


def scan(d, lo):
    u"""Yield (base_reg, first_offset, bytes, {offset: instr_addr}) runs."""
    out = []
    # register values carry across blocks (the routine sets $s0 once and
    # reuses it in several branches); only the buffer resets, so two
    # branches writing the same offsets never merge into one string
    reg, src = {}, {}
    for a, z in blocks(d, lo):
        buf = {}
        for i in range(a, z, 4):
            w = struct.unpack_from('<I', d, i)[0]
            op = w >> 26
            rs, rt = (w >> 21) & 31, (w >> 16) & 31
            imm = w & 0xffff
            s = imm - 0x10000 if imm & 0x8000 else imm
            if op == 0x0f:
                reg[rt], src[rt] = imm << 16, [lo + i]
            elif op == 0x0d and rs in reg:
                reg[rt] = (reg[rs] | imm) & 0xffffffff
                src[rt] = src.get(rs, []) + [lo + i]
            elif op in STORE and rt in reg:
                v = struct.pack('<I', reg[rt])
                base = s - 3 if op == 0x2a else s
                for k in range(4):
                    buf.setdefault((rs, base + k), (v[k], src.get(rt, [])[:], k))
        cells = {}
        for (rsg, off), (byte, imms, k) in buf.items():
            cells.setdefault(rsg, {})[off] = (byte, imms, k)
        for rsg, m in cells.items():
            offs = sorted(m)
            run = [offs[0]]
            for o in offs[1:]:
                if o == run[-1] + 1:
                    run.append(o)
                else:
                    out.append((rsg, run, m))
                    run = [o]
            out.append((rsg, run, m))
    return out


def show(lo, hi, path):
    f = open(path, 'rb')
    f.seek(lo)
    d = f.read(hi - lo)
    f.close()
    for rsg, run, m in scan(d, lo):
        bs = bytes(m[o][0] for o in run)
        if len(bs) < 4:
            continue
        try:
            t = bs.decode('cp932')
        except Exception:
            continue
        if not any(u'\u3000' <= c <= u'\u9fff' or u'\uff01' <= c <= u'\uff5e'
                   for c in t):
            continue
        site = min(a for o in run for a in m[o][1])
        print(u'  site %#08x  $r%-2d +%#04x  %2d bytes  %s'
              % (site, rsg, run[0], len(bs), t))
        for o in run:
            byte, imms, k = m[o]
            print(u'      +%#04x %02x  from %s [byte %d]'
                  % (o, byte, ' '.join('%#x' % x for x in imms), k))


def patch(path, spec):
    u"""Rewrite imm16 fields so the routine builds `english` instead."""
    want = json.load(open(spec, encoding='utf-8'))
    f = open(path, 'r+b')
    for site, new in sorted(want.items()):
        s = int(site, 0)
        f.seek(s - 0x400)
        d = f.read(0x900)
        base = s - 0x400
        target = None
        for rsg, run, m in scan(d, base):
            if min(a for o in run for a in m[o][1]) == s:
                bs = bytes(m[o][0] for o in run)
                if len(bs) >= 4:
                    target = (run, m, bs)
                    break
        if target is None:
            print(u'  %s: no literal run starts here' % site)
            continue
        run, m, bs = target
        nb = new.encode('cp932')
        if len(nb) > len(bs):
            print(u'  %s: %r is %d bytes, budget %d'
                  % (site, new, len(nb), len(bs)))
            continue
        nb = nb.ljust(len(bs), b' ')
        # group the run's bytes by the (lui, ori) pair that carries them
        groups = {}
        for idx, o in enumerate(run):
            byte, imms, k = m[o]
            groups.setdefault(tuple(imms), {})[k] = idx
        for imms, kmap in groups.items():
            word = bytearray(4)
            for k, idx in kmap.items():
                word[k] = nb[idx]
            v = struct.unpack('<I', bytes(word))[0]
            hi16, lo16 = v >> 16, v & 0xffff
            for a in imms:
                f.seek(a)
                w = struct.unpack('<I', f.read(4))[0]
                op = w >> 26
                imm = hi16 if op == 0x0f else lo16
                f.seek(a)
                f.write(struct.pack('<I', (w & 0xffff0000) | imm))
        print(u'  %s: %s -> %s' % (site, bs.decode('cp932'), new))
    f.close()


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        show(int(sys.argv[2], 0), int(sys.argv[3], 0),
             sys.argv[4] if len(sys.argv) > 4 else 'iso/srwz.bin')
    else:
        patch(sys.argv[2], sys.argv[3])
