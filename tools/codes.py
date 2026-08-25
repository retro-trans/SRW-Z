"""Frequency-analyse the control codes embedded in STAGE.BIN dialogue.

Walk the text regions; whenever Shift-JIS decoding breaks, capture the run of
non-text bytes until text resumes. Common short codes are almost always
formatting (line break, wait, speaker, colour); rare long ones are usually
scenario opcodes that happen to sit next to text.
"""
import sys
import os
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sjisscan import is_lead, is_trail

data = open(sys.argv[1], "rb").read()
regions = json.load(open(sys.argv[2], encoding="utf-8"))

codes = collections.Counter()
by_len = collections.Counter()
context = {}

for r in regions:
    start, n = r["offset"], r["nbytes"]
    chunk = data[start:start + n]
    i = 0
    while i < len(chunk):
        if i + 1 < len(chunk) and is_lead(chunk[i]) and is_trail(chunk[i + 1]):
            i += 2
            continue
        # non-text run
        j = i
        while j < len(chunk):
            if j + 1 < len(chunk) and is_lead(chunk[j]) and is_trail(chunk[j + 1]):
                break
            j += 1
        run = chunk[i:j]
        if run:
            codes[bytes(run)] += 1
            by_len[len(run)] += 1
            if bytes(run) not in context:
                lo = max(0, i - 10)
                before = chunk[lo:i].decode("shift_jis", errors="replace")
                after = chunk[j:j + 10].decode("shift_jis", errors="replace")
                context[bytes(run)] = (before, after)
        i = j if j > i else i + 1

print("distinct codes: %d   total occurrences: %d"
      % (len(codes), sum(codes.values())))
print("\n=== RUN LENGTH DISTRIBUTION ===")
for ln, cnt in sorted(by_len.items())[:12]:
    print("   %2d bytes : %6d" % (ln, cnt))

print("\n=== 30 MOST COMMON CODES ===")
print("   %-16s %7s  context" % ("BYTES", "COUNT"))
for run, cnt in codes.most_common(30):
    b, a = context[run]
    print("   %-16s %7d  ...%s [CODE] %s..."
          % (" ".join("%02X" % x for x in run), cnt, b[-8:], a[:8]))
