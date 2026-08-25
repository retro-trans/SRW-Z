"""Apply English UI strings to the boot ELF, in place.

Every replacement is verified against the ELF's actual bytes at that offset
before writing, so a stale or mistyped offset fails loudly instead of
corrupting executable data.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import Patcher
from elf_ui_en import ELF_UI

src, dst = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "ascii"

data = open(src, "rb").read()
p = Patcher(data)

print("%-12s %-34s -> %s" % ("OFFSET", "ORIGINAL", "ENGLISH"))
print("-" * 88)
bad = 0
for off in sorted(ELF_UI):
    en = ELF_UI[off]
    end = data.find(b"\x00", off)
    if end == -1 or end - off > 300:
        print("  0x%08X  !! no terminated string here -- SKIPPED" % off)
        bad += 1
        continue
    orig = data[off:end]
    try:
        jp = orig.decode("shift_jis")
    except UnicodeDecodeError:
        print("  0x%08X  !! not Shift-JIS -- SKIPPED" % off)
        bad += 1
        continue
    # extend the budget through trailing NUL padding (fixed-width name slots
    # pad e.g. a 4-byte name to 8/16 bytes); keep 1 byte for the terminator
    # and cap the extension so we never creep into real zero-valued data.
    k = end
    while k < len(data) and data[k] == 0 and k - end < 12:
        k += 1
    budget = k - off - 1
    if isinstance(en, bytes):
        if len(en) <= budget:
            p.data[off:off + budget] = en + b"\x00" * (budget - len(en))
            p.applied += 1
            ok = True
        else:
            p.skipped.append((off, repr(en[:24]), "raw too long"))
            ok = False
        print("  0x%08X  <raw bytes, %d/%d>" % (off, len(en), budget))
        continue
    ok = p.replace(off, budget, en, mode=mode)
    print("  0x%08X %-34s -> %-30s %s"
          % (off, jp.replace("\n", " / ")[:34], en[:30], "" if ok else "<< SKIPPED"))

print("\nencoding mode: %s" % mode)
p.report()
print("  offsets rejected before patching: %d" % bad)
p.save(dst)

out = open(dst, "rb").read()
print("\nsize: %d -> %d bytes (%s)"
      % (len(data), len(out), "unchanged" if len(data) == len(out) else "CHANGED"))
