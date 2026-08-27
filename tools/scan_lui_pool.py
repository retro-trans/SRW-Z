# -*- coding: utf-8 -*-
"""Does any CODE hardcode a pool address as a lui/addiu (or lui/ori) pair?

A u32 scan cannot see this: MIPS builds a 32-bit constant from two 16-bit
immediate fields in separate instructions, so 0x0073D628 appears on disc as
`lui rt,0x0074` + `addiu rt,rt,-0x29D8` and matches no 4-byte value anywhere.
If the game reached a pool string this way, repacking would break it silently.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz, pool

elf = open("extracted/SLPS_258.87", "rb").read()
rec = bytes(banlz.decompress_all(open("extracted/DATA_COMPDATA.BN", "rb").read())[0][1])
starts = set(a for a, _, _ in pool.entries(rec))
VBASE, FOFF = 0x100000, 0x1A80
LO, HI = pool.BASE + pool.POOL_LO, pool.BASE + pool.POOL_HI

hits, pairs = [], 0
for i in range(0, len(elf) - 4, 4):
    w = struct.unpack_from("<I", elf, i)[0]
    if (w >> 26) != 0x0F:                       # LUI
        continue
    rt = (w >> 16) & 0x1F
    up = w & 0xFFFF
    if up not in (0x0073, 0x0074, 0x0075, 0x0076):
        continue
    for j in range(i + 4, min(i + 4 + 40, len(elf) - 4), 4):
        w2 = struct.unpack_from("<I", elf, j)[0]
        op = w2 >> 26
        if op == 0x09 and ((w2 >> 21) & 0x1F) == rt and ((w2 >> 16) & 0x1F) == rt:
            imm = w2 & 0xFFFF                    # ADDIU: sign-extended
            addr = (up << 16) + (imm - 0x10000 if imm & 0x8000 else imm)
        elif op == 0x0D and ((w2 >> 21) & 0x1F) == rt:
            addr = (up << 16) | (w2 & 0xFFFF)    # ORI: zero-extended
        else:
            if op == 0x0F and ((w2 >> 16) & 0x1F) == rt:
                break                            # rt reloaded
            continue
        pairs += 1
        if LO <= addr < HI:
            hits.append((i - FOFF + VBASE, addr, (addr - pool.BASE) in starts))
        break

print("lui/addiu pairs with a 0x0073-0x0076 upper half: %d" % pairs)
print("resolving INTO the string pool: %d" % len(hits))
for va, addr, onstart in hits:
    off = addr - pool.BASE
    e = rec.find(b"\x00", off) if 0 <= off < len(rec) else -1
    txt = rec[off:e].decode("cp932", "ignore")[:40] if e > 0 else "?"
    print("   code %#010x -> %#010x (rec %#08x) start=%s %r"
          % (va, addr, off, onstart, txt))
if not hits:
    print("none - no code path hardcodes a pool address, so repacking is safe")
