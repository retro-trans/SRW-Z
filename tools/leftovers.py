"""List every string still containing Japanese in the PATCHED rec001,
decoding with cp932 (shift_jis rejects NEC extensions like the Roman
numeral II in 'Gundam Mk-II', which is how these escaped the first dump).
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

stage = open(sys.argv[1], "rb").read()
total, flags, at = banlz.parse_header(stage, 0x00D860)
data, _ = banlz.decompress_stream(stage, at, total)

out = []
pos = 0
while pos < len(data):
    end = data.find(b"\x00", pos)
    if end == -1:
        break
    raw = data[pos:end]
    if len(raw) >= 4:
        try:
            txt = raw.decode("cp932")
        except UnicodeDecodeError:
            txt = None
        if txt and any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" or "！" <= c <= "･"
                       or c in "「」…●？！" for c in txt):
            out.append((pos, len(raw), txt))
    pos = end + 1

print("%d strings still containing Japanese:" % len(out))
for off, n, txt in out:
    print("0x%06X %3dB %s" % (off, n, txt.replace("\n", "\\n")))
