"""Diff two same-base ELF files (original vs an English-rendering patch) to
extract the font/VWF hack: which code was patched, and what new data was added
into dead space.

Usage: elfdiff.py original.elf patched.elf
"""
import sys
import struct

a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
print("original %d bytes, patched %d bytes" % (len(a), len(b)))
n = min(len(a), len(b))

# find contiguous changed byte ranges, coalescing gaps < 16
runs = []
i = 0
while i < n:
    if a[i] != b[i]:
        start = i
        gap = 0
        while i < n and (a[i] != b[i] or gap < 16):
            if a[i] != b[i]:
                gap = 0
            else:
                gap += 1
            i += 1
        end = i - gap
        runs.append((start, end))
    else:
        i += 1
if len(b) > len(a):
    runs.append((len(a), len(b)))

print("\n%d changed region(s):" % len(runs))
CODE_ADDR = None  # PS2 EE ELF PT_LOAD usually vaddr 0x100000 at file off ~0x1A80
for s, e in runs:
    seg = a[s:e] if e <= len(a) else b''
    old_zero = seg.count(0)
    newseg = b[s:e]
    new_zero = newseg.count(0)
    kind = "APPEND" if s >= len(a) else ("into-dead-space" if old_zero > (e - s) * 0.9 else "PATCH")
    print("  file 0x%06X..0x%06X  (%5d bytes)  %s  old_zero=%d new_zero=%d"
          % (s, e, e - s, kind, old_zero, new_zero))

# dump the first few PATCH regions as hex old vs new for inspection
print("\n=== first small PATCH regions (old -> new) ===")
shown = 0
for s, e in runs:
    if s >= len(a) or (e - s) > 256:
        continue
    if a[s:e].count(0) > (e - s) * 0.9:
        continue
    print("\n-- 0x%06X..0x%06X --" % (s, e))
    for off in range(s, e, 16):
        oa = " ".join("%02X" % x for x in a[off:off + 16])
        ob = " ".join("%02X" % x for x in b[off:off + 16])
        print("  OLD %06X %s" % (off, oa))
        print("  NEW %06X %s" % (off, ob))
    shown += 1
    if shown >= 8:
        break
