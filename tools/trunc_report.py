# -*- coding: utf-8 -*-
"""For every truncated ASCII-quoted row, resolve its Japanese source.

Rows are matched through the POINTER, not by offset: a row that an earlier pass
relocated no longer sits where the Japanese does, so comparing offsets directly
gives the wrong source (or none). The pointer WORD position is stable, so
en_record[p] -> our offset and jp_record[p] -> the japanese offset.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE
BASE = 0x7566F0
OPEN, CLOSE = u"\u300c", u"\u300d"

f = open(sys.argv[1], "rb"); f.seek(LBA * SECTOR)
en = banlz.decompress_all(f.read(SIZE)); f.close()
jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())


def sread(b, o):
    e = b.find(b"\x00", o)
    if e < 0: return None
    try: return b[o:e].decode("cp932")
    except Exception: return None


def slot(b, o):
    e = b.find(b"\x00", o); k = e
    while k < len(b) and b[k] == 0: k += 1
    return k - o, e - o


out = []
for idx in range(len(en)):
    e = en[idx][1]; j = jp[idx][1]
    if e is None or j is None: continue
    e = bytes(e); j = bytes(j)
    ptr = {}
    for p in range(0, min(len(e), len(j)) - 4, 4):
        ve = struct.unpack_from("<I", e, p)[0] - BASE
        vj = struct.unpack_from("<I", j, p)[0] - BASE
        if 0 <= ve < len(e) and 0 <= vj < len(j):
            ptr.setdefault(ve, []).append((p, vj))
    o = 0
    while o < len(e):
        z = e.find(b"\x00", o)
        if z == -1: break
        if z > o:
            s = sread(e, o)
            if s and "\n" in s:
                body = s.split("\n", 1)[1]
                if body[:1] in ('"', "'"):
                    q = body.count(body[0])
                    if q % 2 or s.count(OPEN) != s.count(CLOSE):
                        sl, ln = slot(e, o)
                        src = ""
                        pp = ptr.get(o, [])
                        if pp:
                            src = sread(j, pp[0][1]) or ""
                        out.append((idx, o, ln, sl, s, src,
                                    [hex(p) for p, _ in pp]))
            k = z
            while k < len(e) and e[k] == 0: k += 1
            o = k
        else:
            o = z + 1

print("truncated rows: %d\n" % len(out))
for idx, o, ln, sl, s, src, pp in out:
    print("rec%-4d %#08x len=%-3d slot=%-4d ptr=%s" % (idx, o, ln, sl, ",".join(pp) or "NONE"))
    print("   EN %r" % s.replace("\n", " | "))
    print("   JP %r" % src.replace("\n", " | "))
