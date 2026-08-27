# -*- coding: utf-8 -*-
"""Locate the REAL LIBRARY-menu texture on the disc.

patch_library_menu.py repainted /DATA/JTIM.BIN image #5, which LOOKS exactly
like this menu but is not what the screen draws - the patch changed nothing in
game. The PCSX2 dump gives us the pixels the game actually blits:

    8ed5786b95541a75-2cdd03b431356fe3-00002253            512x256
    8a344e380294371b-2cdd03b431356fe3-r257x257-00002213   257x257

68 distinct colours with PS2 alpha (0/20/50/80/128), so it is 8bpp with a CLUT.
Its CLUT holds these RGBA entries verbatim, so scanning the image for several of
the distinctive ones inside one 1KB window finds the CLUT, and the pixels sit
next to it.

Only a texture stored UNCOMPRESSED is findable this way; if nothing turns up,
the bank is packed and has to be decompressed first.

Usage: find_library_texture.py <iso>
"""
import sys

# distinctive opaque entries from the original dump, rarest-looking first
NEEDLES = [bytes.fromhex(h) for h in
           ("2caa2b80", "0231 0580".replace(" ", ""), "29aa1e80",
            "13382880", "0a331980", "6a826a80", "a5b1a680")]
WINDOW = 2048


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    CH = 1 << 24
    off, prev, hits = 0, b"", []
    while True:
        b = f.read(CH)
        if not b:
            break
        buf = prev + b
        base = off - len(prev)
        i = buf.find(NEEDLES[0])
        while i >= 0:
            lo, hi = max(0, i - WINDOW), i + WINDOW
            w = buf[lo:hi]
            n = sum(1 for nd in NEEDLES[1:] if nd in w)
            if n >= 3:
                hits.append((base + i, n))
            i = buf.find(NEEDLES[0], i + 1)
        prev = buf[-WINDOW * 2:]
        off += len(b)
        if off % (1 << 30) == 0:
            sys.stderr.write("  %d GB\n" % (off >> 30))
            sys.stderr.flush()
    f.close()
    seen, out = set(), []
    for p, n in hits:
        if any(abs(p - q) < WINDOW for q in seen):
            continue
        seen.add(p)
        out.append((p, n))
    print("CLUT candidates: %d" % len(out))
    for p, n in out:
        print("   %#012x  LBA %-9d +%-6d  %d/%d companion entries"
              % (p, p // 2048, p % 2048, n, len(NEEDLES) - 1))


if __name__ == "__main__":
    main()
