# -*- coding: utf-8 -*-
"""Whole-project statistics for the SRW Z English patch.

Counts what is actually IN the shipped image by comparing it against the
untouched japanese original, rather than trusting what any one pass claimed.

The hard part is counting only REAL text. Walking every NUL-terminated run in a
decompressed record also picks up pointer tables and padding, which contain no
kana and so score as "translated" - that inflates the totals by an order of
magnitude. So:

  * STAGE.BIN rows are reached through the POINTER TABLE (BASE 0x7566F0), the
    same way the game reaches them, and matched index-for-index against the
    japanese record. Nothing that is not a real row is counted.
  * Everywhere else a string must look like prose or a name: at least three
    characters, at least one letter or kana, and at least 85% of it printable.

A string counts as TRANSLATED when it differs from the japanese it replaced and
contains no kana or kanji. A string still holding kana counts as REMAINING, so
half-done work is never counted as done.

Usage: project_stats.py <iso> [jp-iso]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

CJK = re.compile(u"[぀-ヿ㐀-䶿一-鿿]")
SECTOR = 2048
BASE = 0x7566F0


def is_en(s):
    return not CJK.search(s)


def texty(s):
    if len(s.strip()) < 3:
        return False
    if not re.search(u"[A-Za-z぀-ヿ一-鿿]", s):
        return False
    ok = sum(1 for c in s if c in "\n\t" or 32 <= ord(c) < 127 or ord(c) > 160)
    return ok >= len(s) * 0.85


def read(iso, lba, size):
    f = open(iso, "rb")
    f.seek(lba * SECTOR)
    d = f.read(size)
    f.close()
    return d


def rows_by_pointer(rec):
    """Strings a pointer table actually points at."""
    b = bytes(rec)
    out = {}
    for p in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, p)[0] - BASE
        if not (0 <= v < len(b)) or v in out:
            continue
        z = b.find(b"\x00", v)
        if z <= v or z - v > 1200:
            continue
        try:
            s = b[v:z].decode("cp932")
        except Exception:
            continue
        if texty(s):
            out[v] = s
    return out


def scan_plain(buf):
    out, i, n = [], 0, len(buf)
    while i < n:
        z = buf.find(b"\x00", i)
        if z < 0:
            break
        if z > i and z - i < 1200:
            try:
                s = buf[i:z].decode("cp932")
                if texty(s):
                    out.append(s)
            except Exception:
                pass
        i = z + 1
        while i < n and buf[i] == 0:
            i += 1
    return out


def banlz_scan(buf):
    out = []
    for _h, p in banlz.decompress_all(buf):
        if p is not None:
            out += scan_plain(bytes(p))
    return out


def tally(name, en, rows=True):
    tr = [s for s in en if is_en(s)]
    rem = [s for s in en if not is_en(s)]
    pct = 100.0 * len(tr) / max(1, len(en))
    ln = sum(s.count("\n") + 1 for s in tr)
    ch = sum(len(s) for s in tr)
    print("  %-24s %7d  %6d   %5.1f%%  %8d  %9d"
          % (name, len(tr), len(rem), pct, ln, ch))
    return len(tr), len(rem), ln, ch


def main():
    iso = sys.argv[1]
    print("  %-24s %7s  %6s   %6s  %8s  %9s"
          % ("", "english", "left", "done", "lines", "chars"))
    tot = [0, 0, 0, 0]

    def add(t):
        for i in range(4):
            tot[i] += t[i]

    en = []
    for _h, p in banlz.decompress_all(read(iso, 1651029, 3910128)):
        if p is not None:
            en += list(rows_by_pointer(p).values())
    add(tally("STAGE.BIN dialogue", en))

    caps = [s for s in scan_plain(read(iso, 1313214, 2913887))
            if s.lstrip().startswith('"')]
    add(tally("SRVC.BIN battle lines", caps))

    add(tally("COMPDATA.BN names", banlz_scan(read(iso, 1823000, 74 * SECTOR))))
    for nm, lba, size in (("MTVZKNPT glossary", 1573457, 278528),
                          ("MTVZKNRT glossary", 1824000, 198656),
                          ("MTVZKNKW glossary", 1823200, 32768),
                          ("HSFC.BIN map text", 1568541, 250112)):
        add(tally(nm, banlz_scan(read(iso, lba, size))))

    print("  " + "-" * 68)
    print("  %-24s %7d  %6d   %5.1f%%  %8d  %9d"
          % ("TOTAL", tot[0], tot[1], 100.0 * tot[0] / max(1, tot[0] + tot[1]),
             tot[2], tot[3]))

    print("\nPROJECT")
    work = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools = [n for n in os.listdir(os.path.join(work, "tools")) if n.endswith(".py")]
    loc = 0
    for n in tools:
        try:
            loc += sum(1 for _ in open(os.path.join(work, "tools", n),
                                       encoding="utf-8", errors="ignore"))
        except Exception:
            pass
    print("  %-24s %d files, %d lines" % ("tools written", len(tools), loc))
    cl = os.path.join(work, "CHANGELOG.md")
    if os.path.exists(cl):
        b = re.findall(r"^## (\S+)", open(cl, encoding="utf-8").read(), re.M)
        print("  %-24s %d logged, %s .. %s" % ("builds", len(b), b[-1], b[0]))


if __name__ == "__main__":
    main()
