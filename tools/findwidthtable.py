"""Find a proportional-font width table in an ELF: a run of ~95 small byte
values (per-character advances, typically 2..14) covering ASCII 0x20..0x7E.
Space (first entry) is usually small; letters vary; digits often equal.
"""
import sys

data = open(sys.argv[1], "rb").read()
best = []
i = 0
n = len(data)
while i < n - 40:
    # candidate run of bytes all in 1..16
    if 1 <= data[i] <= 16:
        j = i
        while j < n and 1 <= data[j] <= 16:
            j += 1
        run = data[i:j]
        if len(run) >= 40:            # long enough to be a font metric table
            # heuristic: some variety (not all identical), plausible letter widths
            uniq = len(set(run))
            if uniq >= 4:
                best.append((i, len(run), run))
        i = j
    else:
        i += 1

best.sort(key=lambda r: -r[1])
print("candidate width tables (offset, len, first ~40 values):")
for off, ln, run in best[:12]:
    vals = " ".join(str(b) for b in run[:48])
    print("  0x%06X  len=%d  [%s%s]" % (off, ln, vals, " ..." if ln > 48 else ""))
