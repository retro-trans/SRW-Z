# -*- coding: utf-8 -*-
"""How much narrower would English text be with proportional advances?

The shipped font is HALF-WIDTH, not variable-width: every Latin glyph advances a
fixed 12px (Japanese 24px). This reads the 69 half-width letterforms actually
stamped into the master font by patch_hwfont, measures each one's real ink
width, and weights that against the shipped English dialogue to get the true
saving - rather than guessing at it.

Atlas format (patch_hwfont): 69 glyphs, order . " ' ! , - ? 0-9 A-Z a-z,
12px wide 2bpp MSB-first = 3 bytes/row, 24 rows = 72 B/glyph, at CAVE+0x540.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

VBASE, FOFF = 0x100000, 0x1A80
CAVE = 0x188470
ATLAS_VA = CAVE + 0x540
NART, GLYPH_BYTES, CW = 69, 72, 12
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + \
        list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
SIDE = 1          # 1px right sidebearing, the usual minimum

iso = sys.argv[1]
f = open(iso, "rb"); f.seek(455 * 2048); elf = f.read(3471624); f.close()
base = ATLAS_VA - VBASE + FOFF
atlas = elf[base:base + NART * GLYPH_BYTES]

width = {}
for g, code in enumerate(CHARS):
    cell = atlas[g * GLYPH_BYTES:(g + 1) * GLYPH_BYTES]
    right = -1
    for row in range(GLYPH_BYTES // 3):
        r = cell[row * 3:row * 3 + 3]
        bits = (r[0] << 16) | (r[1] << 8) | r[2]
        for x in range(CW):
            if (bits >> (22 - 2 * x)) & 3:
                right = max(right, x)
    width[chr(code)] = (right + 1 + SIDE) if right >= 0 else 4
width[" "] = 5

blank = [c for c, w in width.items() if w == 0]
print("glyphs measured: %d%s" % (len(width), "  (blank: %r)" % blank if blank else ""))
print("narrowest: %s" % sorted(width.items(), key=lambda kv: kv[1])[:10])
print("widest   : %s" % sorted(width.items(), key=lambda kv: -kv[1])[:8])

# weight by the real corpus
f = open(iso, "rb"); f.seek(LBA * SECTOR)
items = banlz.decompress_all(f.read(SIZE)); f.close()
freq = collections.Counter()
lines = 0
fixed_px = prop_px = 0
for hdr, data in items:
    if data is None:
        continue
    b = bytes(data); i = 0
    while i < len(b):
        j = b.find(b"\x00", i)
        if j == -1: j = len(b)
        if j - i > 4:
            try: s = b[i:j].decode("cp932")
            except Exception:
                i = j + 1; continue
            if u"\u300c" in s:
                for ln in s.split("\n")[1:]:
                    if not ln: continue
                    lines += 1
                    for ch in ln:
                        if ch in width:
                            freq[ch] += 1
                            fixed_px += CW
                            prop_px += width[ch]
                        else:
                            fixed_px += 24
                            prop_px += 24
        i = j + 1
print("\ndialogue body lines measured: %d" % lines)
print("total width fixed half-width : %d px" % fixed_px)
print("total width proportional     : %d px" % prop_px)
print("SAVING: %.1f%%" % (100.0 * (fixed_px - prop_px) / fixed_px))
lat = sum(freq.values())
print("latin glyphs: %d, mean advance %.2f px (vs 12 fixed)"
      % (lat, sum(width[c] * n for c, n in freq.items()) / float(lat)))
