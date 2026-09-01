# -*- coding: utf-8 -*-
"""Zero-cost audit: run patch_compdata's in-memory transforms and report the
byte ranges it changes, to confirm every write stays inside the name/title/bio
string regions and never touches combat/stat structures."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import patch_compdata as pc
from patch import encode as menc
from compdata_en import PILOTS, TITLES, BIOS, SHORT, AMBIG

comp = open(r"E:\Projects\SRW Z\_work\extracted\DATA_COMPDATA.BN", "rb").read()
recs = banlz.decompress_all(comp)
orig, _ = banlz.decompress_record(comp, recs[0][0])
d = bytearray(orig)

# replicate main()'s transforms exactly
over = []
wmap = json.load(open(r"E:\Projects\SRW Z\_work\analysis\weapons_en.json", encoding="utf-8"))
for jp, en in sorted(wmap.items(), key=lambda x: -len(x[0])):
    enb = menc(en, "menu"); jb = jp.encode("cp932")
    i = d.find(jb, pc.WPN_LO)
    while 0 <= i < pc.WPN_HI:
        j = i + len(jb)
        if d[j] == 0 and d[i-1] == 0:
            k = j
            while d[k] == 0: k += 1
            budget = k - i - 1
            if len(enb) <= budget:
                d[i:i+budget] = enb + bytes(budget - len(enb))
        i = d.find(jb, i + 1)
for jp, en in sorted(pc.load_units().items(), key=lambda x: -len(x[0])):
    pc.field_replace(d, jp, en, pc.UNIT_LO, pc.UNIT_HI, over)
for jp, en in sorted(PILOTS.items(), key=lambda x: -len(x[0])):
    pc.field_replace(d, jp, en, 0, len(d), over)
for jp, en in sorted(TITLES.items(), key=lambda x: -len(x[0])):
    pc.field_replace(d, jp, en, pc.TITLE_LO, pc.TITLE_HI, over)
for jp, rules in AMBIG.items():
    jb = jp.encode("cp932"); i = d.find(jb)
    while i >= 0:
        j = i + len(jb)
        if d[j] == 0 and d[i-1] in (0, 2):
            around = bytes(d[max(0, i-0x80):i+0x80])
            for anchor, en in rules:
                if anchor in around:
                    k = j
                    while d[k] == 0: k += 1
                    budget = k - i - 1; eb = en.encode("cp932")
                    if len(eb) <= budget:
                        d[i:i+budget] = eb + b"\x00" * (budget - len(eb))
                    break
        i = d.find(jb, i + 1)
pc.bio_replace(d, BIOS, 0, len(d), over)

# diff into contiguous changed ranges
ranges = []
i = 0; N = len(orig)
while i < N:
    if d[i] != orig[i]:
        s = i
        while i < N and d[i] != orig[i]: i += 1
        ranges.append((s, i))
    else:
        i += 1

# known string regions
REGIONS = {
    "WPN(0x66380-0x6C000)": (0x66380, 0x6C000),
    "UNIT(0x6C000-0x72000)": (0x6C000, 0x72000),
    "TITLE(0x72000-0x74000)": (0x72000, 0x74000),
}
def region_of(a, b):
    for name, (lo, hi) in REGIONS.items():
        if a >= lo and b <= hi:
            return name
    return "OTHER"

print("decompressed size:", N)
print("changed ranges:", len(ranges))
outside = []
from collections import Counter
byreg = Counter()
for a, b in ranges:
    r = region_of(a, b)
    byreg[r] += 1
    if r == "OTHER":
        outside.append((a, b))
for r, c in byreg.items():
    print("  %-24s %d ranges" % (r, c))
print()
print("Ranges OUTSIDE the name/title/wpn regions (pilots+bios scan whole buf):", len(outside))
lo_all = min(a for a,_ in ranges); hi_all = max(b for _,b in ranges)
print("overall changed span: 0x%X .. 0x%X" % (lo_all, hi_all))
# show a sample of OTHER ranges with context bytes to judge if they hit binary/stat data
for a, b in outside[:40]:
    ctx = bytes(orig[max(0,a-2):b+2])
    txt = bytes(d[a:b]).decode("cp932", "replace")
    print("  0x%06X-0x%06X (%dB) new=%r" % (a, b, b-a, txt[:40]))
