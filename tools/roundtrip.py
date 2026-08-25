"""Round-trip proof: parse SRVC.BIN + SRVC.SEG, rebuild both untouched,
demand byte equality. If this passes, reinsertion is provably safe.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc

bin_path, seg_path = sys.argv[1], sys.argv[2]
data = open(bin_path, "rb").read()
seg_data = open(seg_path, "rb").read()
seg = srvc.read_seg(seg_data)

print("SEG entries: %d  (last = 0x%X, file size = 0x%X)" % (len(seg), seg[-1], len(data)))
blocks = srvc.parse(data, seg)

text_blocks = [b for b in blocks if b.has_text]
print("\nblocks           : %d" % len(blocks))
print("  with text      : %d" % len(text_blocks))
print("  opaque/no text : %d" % (len(blocks) - len(text_blocks)))
print("index entries    : %s" % "{:,}".format(sum(len(b.ids) for b in text_blocks)))
print("strings          : %s" % "{:,}".format(sum(len(b.strings) for b in text_blocks)))
print("non-empty strings: %s" % "{:,}".format(
    sum(1 for b in text_blocks for s in b.strings if s)))

rebuilt, rebuilt_seg = srvc.build(blocks)
print("\nBIN original %s -> rebuilt %s" % (
    "{:,}".format(len(data)), "{:,}".format(len(rebuilt))))
print("SEG original %s -> rebuilt %s" % (
    "{:,}".format(len(seg_data)), "{:,}".format(len(rebuilt_seg))))

ok = True
if rebuilt != data:
    ok = False
    print("\n!!! BIN MISMATCH !!!")
    for i in range(min(len(data), len(rebuilt))):
        if data[i] != rebuilt[i]:
            print("  first difference at 0x%X" % i)
            lo = max(0, i - 24)
            print("  original: %s" % " ".join("%02X" % b for b in data[lo:i + 24]))
            print("  rebuilt : %s" % " ".join("%02X" % b for b in rebuilt[lo:i + 24]))
            for bi, b in enumerate(blocks):
                if b.start <= i:
                    owner = bi
            print("  in block %d (0x%X, has_text=%s)"
                  % (owner, blocks[owner].start, blocks[owner].has_text))
            break
if rebuilt_seg != seg_data:
    ok = False
    print("\n!!! SEG MISMATCH !!!")
    orig = srvc.read_seg(seg_data)
    new = srvc.read_seg(rebuilt_seg)
    for i, (a, b) in enumerate(zip(orig, new)):
        if a != b:
            print("  first difference at entry %d: 0x%X vs 0x%X" % (i, a, b))
            break

print("\n*** ROUND-TRIP EXACT ***" if ok else "\n*** ROUND-TRIP FAILED ***")
sys.exit(0 if ok else 1)
