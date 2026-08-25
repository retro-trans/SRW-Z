# -*- coding: utf-8 -*-
"""Find memory in the boot ELF that is genuinely unused, so a code cave can live
there without displacing anything.

Every earlier cave location failed because "unreferenced" was decided too
loosely. This marks an address as USED if any of these hold:
  * a u32 anywhere in the image equals it (function-pointer tables - this is how
    0x121810 was reached, and why a j/jal-only scan missed it)
  * a j / jal targets it
  * a lui+addiu/ori pair builds it
  * it lies inside a function whose entry was reached by the above (walk forward
    to the terminating `jr ra`)
Then it reports the largest runs nothing touches.

Usage: find_free_space.py [min_bytes]
"""
import struct, sys

VB, FO, FSZ = 0x100000, 0x1A80, 0x34BC80
elf = open(r"E:\Projects\SRW Z\_work\hwbuild\orig.elf", "rb").read()
seg = elf[FO:FO + FSZ]
N = FSZ

used = bytearray(N)          # per byte
entries = set()


def mark(va, n=4):
    o = va - VB
    if 0 <= o < N:
        used[o:o + n] = b"\x01" * min(n, N - o)


# 1) pointer-table style references (u32 values that look like addresses)
for i in range(0, N - 4, 4):
    w = struct.unpack_from("<I", seg, i)[0]
    if VB <= w < VB + N:
        entries.add(w)
        mark(w)

# 2) j / jal targets, and lui+lo pairs
pend = {}
for i in range(0, N - 4, 4):
    w = struct.unpack_from("<I", seg, i)[0]
    op = w >> 26
    if op in (2, 3):                       # j / jal
        t = (w & 0x03FFFFFF) << 2
        if VB <= t < VB + N:
            entries.add(t); mark(t)
    elif op == 0x0F:                       # lui rt, imm
        pend[(w >> 16) & 0x1F] = (w & 0xFFFF, i)
    elif op in (0x09, 0x0D):               # addiu / ori rt, rs, imm
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        if rs in pend:
            hi, at = pend[rs]
            if i - at <= 64:
                lo = w & 0xFFFF
                a = (hi << 16) + (lo - 0x10000 if op == 0x09 and lo & 0x8000 else lo)
                if VB <= a < VB + N:
                    entries.add(a); mark(a)
        if rt in pend and rt != rs:
            pend.pop(rt, None)

# 3) walk each entry forward to the end of its function (jr ra + delay slot)
for e in entries:
    o = e - VB
    if not (0 <= o < N):
        continue
    j = o
    limit = o + 0x4000
    while j + 8 <= N and j < limit:
        w = struct.unpack_from("<I", seg, j)[0]
        used[j:j + 4] = b"\x01\x01\x01\x01"
        if w == 0x03E00008:                # jr ra
            used[j + 4:j + 8] = b"\x01\x01\x01\x01"   # delay slot
            break
        j += 4

minlen = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
runs = []
i = 0
while i < N:
    if not used[i]:
        s = i
        while i < N and not used[i]:
            i += 1
        if i - s >= minlen:
            runs.append((VB + s, i - s))
    else:
        i += 1
runs.sort(key=lambda r: -r[1])
print("entries found: %d" % len(entries))
print("free runs >= %d bytes: %d" % (minlen, len(runs)))
for va, ln in runs[:15]:
    blob = seg[va - VB: va - VB + ln]
    z = blob.count(0)
    print("   vaddr 0x%06X  len %6d (%.1fKB)  zero%%=%d" % (va, ln, ln / 1024, 100 * z // ln))
