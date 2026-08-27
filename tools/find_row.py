# -*- coding: utf-8 -*-
"""Find dialogue rows in STAGE by substring, printing record + offset."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

needles = [a for a in sys.argv[2:] if not a.startswith("-")]
f = open(sys.argv[1], "rb"); f.seek(LBA * SECTOR)
items = banlz.decompress_all(f.read(SIZE)); f.close()
for idx, (hdr, data) in enumerate(items):
    if data is None: continue
    buf = bytes(data); i = 0
    while i < len(buf):
        j = buf.find(b"\x00", i)
        if j == -1: j = len(buf)
        seg = buf[i:j]
        if len(seg) > 2:
            try: s = seg.decode("cp932")
            except Exception:
                i = j + 1; continue
            if any(n in s for n in needles):
                k = j
                while k < len(buf) and buf[k] == 0: k += 1
                print("rec%-4d off=%#08x len=%-4d slot=%-4d %r"
                      % (idx, i, j - i, k - i, s.replace("\n", " | ")))
        i = j + 1
