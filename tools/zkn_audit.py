# -*- coding: utf-8 -*-
"""Audit the in-game LIBRARY (encyclopedia) text as it exists in the image.

The ZKN payloads are XOR-0x5E obfuscated (see zkn.deobf), so decompressing a
record and decoding it as cp932 yields NOISE. A search over that noise finds
nothing and looks like a clean result - it is not. Always go through
zkn.parse(zkn.payload_of(rec)).

  MTVZKNPT  411 character entries   CHFN CHNN PRDC ACTR DSCR DSC2
  MTVZKNRT  321 robot entries       PRDC RBTN PLTN HEIT WEIT DSCR DSC2 KANA
  MTVZKNKW   52 glossary entries    WORD SRCE DSCR DSC2

Usage:
  zkn_audit.py <iso> --terms         list every KW term (WORD + SRCE)
  zkn_audit.py <iso> --stale         search all three files for old spellings
  zkn_audit.py <iso> --grep <text>   find entries containing text
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import zkn

SEC = 2048
REGIONS = {"PT": (1573457, 278528),
           "RT": (1824000, 198656),
           "KW": (1823200, 32768)}

TEXT_TAGS = ("WORD", "SRCE", "CHFN", "CHNN", "PRDC", "ACTR", "RBTN", "PLTN",
             "DSCR", "DSC2", "KANA")

STALE = ["Kashimaru", "Kashimar", "Norbu", "Norub", "Tsine", "Tziine",
         "Zaidel", "Zaydel", "Zeidel", "Barre", "Leven", "Leben", "Teraru",
         "Gendarme", "Vodarac Wheel", "Mu Dimension", "Overlap", "Hughi",
         "Gagaan", "Taiji"]


def read_region(iso, key):
    lba, size = REGIONS[key]
    f = open(iso, "rb")
    f.seek(lba * SEC)
    raw = f.read(size)
    f.close()
    heads = banlz.decompress_all(bytearray(raw))
    out = []
    for ri in range(len(heads)):
        try:
            dd, _ = banlz.decompress_record(raw, heads[ri][0])
        except Exception:
            continue
        out.append((ri, bytes(dd)))
    return out


def fields(rec):
    """Yield (tag, text) for every decodable text chunk."""
    try:
        magic, kind, ver, chunks = zkn.parse(zkn.payload_of(rec))
    except Exception:
        return
    for tag, off, data in chunks:
        if isinstance(data, int) or tag not in TEXT_TAGS:
            continue
        try:
            t = data.decode("cp932").rstrip("\x00").rstrip()
        except Exception:
            continue
        if t:
            yield tag, t


def main():
    iso = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--terms"
    needle = sys.argv[3] if len(sys.argv) > 3 else None

    if mode == "--terms":
        for ri, rec in read_region(iso, "KW"):
            d = dict(fields(rec))
            print("%-3d %-32s [%s]" % (ri, d.get("WORD", "?"),
                                       d.get("SRCE", "")[:34]))
        return

    if mode == "--stale":
        hits = {}
        for key in ("PT", "RT", "KW"):
            recs = read_region(iso, key)
            got = 0
            for ri, rec in recs:
                for tag, t in fields(rec):
                    got += 1
                    for w in STALE:
                        if w in t:
                            hits.setdefault(w, []).append((key, ri, tag, t[:60]))
            print("%s: %d records, %d text fields read" % (key, len(recs), got))
        print()
        if not hits:
            print("no stale spellings in the library")
        for w in sorted(hits):
            print("  %-14s %d" % (w, len(hits[w])))
            for h in hits[w][:4]:
                print("      %s rec%-4d %-4s %s" % h)
        return

    if mode == "--grep" and needle:
        for key in ("PT", "RT", "KW"):
            for ri, rec in read_region(iso, key):
                for tag, t in fields(rec):
                    if needle in t:
                        print("%s rec%-4d %-4s %s" % (key, ri, tag, t[:90]))


if __name__ == "__main__":
    main()
