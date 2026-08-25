"""Extract files out of the PS2 ISO by LBA + size, using the TSV from isolist.py.

Skips the bulk media (audio bank, video, BGM, disc padding) by default --
those are gigabytes of data that cannot contain script text.
"""
import sys
import os

SECTOR = 2048
SKIP = ("/SOUND/CCC.MSB", "/MPG/OPPRG.PSS", "/MPG/EDPRG.PSS",
        "/MPG/MIDPRG.PSS", "/BGM/BGM.BIN", "/DMY/DMY.BIN")


def main(iso, tsv, outdir, limit=None):
    os.makedirs(outdir, exist_ok=True)
    rows = []
    with open(tsv, encoding="utf-8") as f:
        next(f)
        for line in f:
            path, size, lba = line.rstrip("\n").split("\t")
            rows.append((path, int(size), int(lba)))

    total = 0
    with open(iso, "rb") as src:
        for path, size, lba in rows:
            if path in SKIP:
                print("  skip (media)  %-28s %s bytes" % (path, "{:,}".format(size)))
                continue
            if limit and size > limit:
                print("  skip (>limit) %-28s %s bytes" % (path, "{:,}".format(size)))
                continue
            flat = path.lstrip("/").replace("/", "_")
            dst = os.path.join(outdir, flat)
            src.seek(lba * SECTOR)
            remaining = size
            with open(dst, "wb") as out:
                while remaining > 0:
                    chunk = src.read(min(remaining, 8 * 1024 * 1024))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
            total += size
            print("  extracted     %-28s %s bytes" % (path, "{:,}".format(size)))
    print("\ntotal extracted: %.1f MB" % (total / 1e6))


if __name__ == "__main__":
    lim = int(sys.argv[4]) if len(sys.argv) > 4 else None
    main(sys.argv[1], sys.argv[2], sys.argv[3], lim)
