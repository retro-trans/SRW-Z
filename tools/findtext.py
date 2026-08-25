"""Search every extracted file for a Japanese phrase in raw Shift-JIS.

If a compressed-looking phrase also exists uncompressed somewhere, that copy
is the one worth translating.
"""
import sys
import os
import glob

needles = [s.encode("shift_jis") for s in sys.argv[2:]]
if not needles:
    print("give one or more phrases to search for")
    sys.exit(1)

print("searching for: %s\n" % ", ".join(sys.argv[2:]))
found_any = False
for path in sorted(glob.glob(sys.argv[1])):
    if not os.path.isfile(path):
        continue
    data = open(path, "rb").read()
    for raw, disp in zip(needles, sys.argv[2:]):
        pos = data.find(raw)
        hits = 0
        while pos != -1:
            hits += 1
            if hits <= 3:
                lo = max(0, pos - 40)
                ctx = data[lo:pos + 60].decode("shift_jis", errors="replace")
                print("  %-24s 0x%08X  %s" % (os.path.basename(path), pos,
                                              ctx.replace("\n", " ")))
            pos = data.find(raw, pos + 1)
        if hits:
            found_any = True
            print("    -> %r found %d time(s) in %s\n" % (disp, hits, os.path.basename(path)))

if not found_any:
    print("  not found in plain Shift-JIS anywhere")
