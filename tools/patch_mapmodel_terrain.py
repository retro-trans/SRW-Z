# -*- coding: utf-8 -*-
"""Terrain-zone names inside MAPMODEL.BIN (LBA 1652964, 55 MB).

The deploy panel's "< 荒地 >" line is not in the ELF, COMPDATA, any banlz
bank, or a code-built string - a raw scan of the whole image finds those
names ONLY here.  MAPMODEL holds each map's node-name table: short
NUL-terminated names separated by 1-2 byte tags, mixed with ASCII names
like "Frame".  The map-specific entries (議会事堂 "Parliament", イノセント
ドーム "Innocent Dome") are exactly what that panel cycles through, which
is why the names live with the map instead of in a global table.

Edits are IN PLACE and NUL-padded to the original length, so the file
keeps its size and every offset inside it stays valid - the safe way to
touch a 55 MB binary whose format is only partly understood.  ASCII is
proven acceptable in these slots by the engine's own "Frame" entries.
Replacing is idempotent and --revert is exact (same lengths both ways).

Usage: patch_mapmodel_terrain.py <iso> [--revert] [--dry-run]
"""
import sys

LBA, SIZE, SECTOR = 1652964, 55136688, 2048
CHUNK, OVERLAP = 1 << 23, 64

# jp -> en; the English must be SHORTER than the Japanese + its NUL, so the
# terminator is always written.  Budget is len(cp932) bytes.
TERRAIN = {
    "平地": "Flat",
    "荒地": "Arid",
    "道路": "Road",
    "宇宙空間": "Space",
    "雪原": "Snow",
    "ビル街": "City",
}


def build(revert):
    """[(search, replace)] - both the same length, NUL-terminated."""
    out = []
    for jp, en in TERRAIN.items():
        j = jp.encode("cp932") + b"\x00"
        e = en.encode("ascii")
        assert len(e) < len(j), "%r does not fit %r" % (en, jp)
        e = e + b"\x00" * (len(j) - len(e))
        out.append((e, j, jp, en) if revert else (j, e, jp, en))
    return out


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    dry = "--dry-run" in sys.argv
    subs = build(revert)
    counts = {jp: 0 for _s, _r, jp, _e in subs}
    iso = open(iso_path, "r+b")
    pos = 0
    while pos < SIZE:
        n = min(CHUNK + OVERLAP, SIZE - pos)
        iso.seek(LBA * SECTOR + pos)
        data = iso.read(n)
        out = data
        for search, repl, jp, _en in subs:
            hit = out.count(search)
            if hit:
                counts[jp] += hit
                out = out.replace(search, repl)
        if out != data and not dry:
            iso.seek(LBA * SECTOR + pos)
            iso.write(out)
        pos += CHUNK                      # overlap is re-scanned, harmless:
    iso.close()                           # every substitution is same-length
    for jp, en in TERRAIN.items():
        print("  %-6s -> %-6s %4d" % (jp, en, counts[jp]))
    print("%s %d replacements" % ("would make" if dry else "made",
                                  sum(counts.values())))


if __name__ == "__main__":
    main()
