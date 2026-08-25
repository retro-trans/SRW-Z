"""Scan a binary for runs of plausible Shift-JIS Japanese text.

Two questions this answers:
  1. Is there *any* readable Japanese in this file? (-> plaintext, good news)
  2. If not, is the file compressed or encrypted? (-> high entropy, bad news)

Shift-JIS double-byte:  lead 0x81-0x9F / 0xE0-0xEF, trail 0x40-0x7E / 0x80-0xFC
Half-width katakana:    0xA1-0xDF (single byte)
"""
import sys
import os
import math
from collections import Counter


def entropy(data):
    if not data:
        return 0.0
    c = Counter(data)
    n = len(data)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def is_trail(b):
    return (0x40 <= b <= 0x7E) or (0x80 <= b <= 0xFC)


def find_runs(data, min_chars=3):
    """Yield (offset, text) for runs of >= min_chars Japanese characters."""
    runs = []
    i = 0
    n = len(data)
    while i < n - 1:
        if is_lead(data[i]) and is_trail(data[i + 1]):
            start = i
            count = 0
            while i < n - 1 and is_lead(data[i]) and is_trail(data[i + 1]):
                i += 2
                count += 1
            if count >= min_chars:
                raw = data[start:i]
                try:
                    txt = raw.decode("shift_jis")
                    runs.append((start, txt))
                except UnicodeDecodeError:
                    pass
        else:
            i += 1
    return runs


def analyse(path, show=12):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        # sample up to 4 MB from the head for large files
        data = f.read(min(size, 4 * 1024 * 1024))

    ent = entropy(data)
    runs = find_runs(data)
    jp_chars = sum(len(t) for _, t in runs)

    verdict = "COMPRESSED/ENCRYPTED" if ent > 7.5 else ("plain-ish" if ent < 6.0 else "mixed")
    print("%-46s %10s  entropy %.2f  %-22s %4d runs  %5d JP chars"
          % (os.path.basename(path), "{:,}".format(size), ent, verdict, len(runs), jp_chars))

    for off, txt in runs[:show]:
        preview = txt[:60].replace("\n", " ")
        print("      +0x%08X  %s" % (off, preview))
    return ent, len(runs), jp_chars


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyse(p)
