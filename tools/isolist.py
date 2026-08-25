"""Dump the full ISO9660 file tree of a PS2 disc image.

Emits a TSV: path, size, LBA, extension  -- sorted largest first,
plus a per-extension summary so the big data archives stand out.
"""
import sys
import struct
from collections import defaultdict

SECTOR = 2048


def read_sector(f, lba, count=1):
    f.seek(lba * SECTOR)
    return f.read(SECTOR * count)


def parse_dir(f, lba, size, path, out, depth=0):
    """Walk an ISO9660 directory extent, recursing into subdirectories."""
    if depth > 12:
        return
    data = read_sector(f, lba, max(1, (size + SECTOR - 1) // SECTOR))
    off = 0
    while off < len(data):
        rec_len = data[off]
        if rec_len == 0:
            # padding to the end of this sector; jump to the next one
            off = (off // SECTOR + 1) * SECTOR
            if off >= len(data):
                break
            continue
        rec = data[off:off + rec_len]
        if len(rec) < 33:
            break
        ext_lba = struct.unpack("<I", rec[2:6])[0]
        ext_len = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        name_len = rec[32]
        name = rec[33:33 + name_len]

        if name_len == 1 and name in (b"\x00", b"\x01"):
            off += rec_len
            continue

        nm = name.decode("ascii", "replace")
        if ";" in nm:
            nm = nm.split(";")[0]
        full = path + "/" + nm

        if flags & 0x02:
            out.append((full + "/", 0, ext_lba, True))
            parse_dir(f, ext_lba, ext_len, full, out, depth + 1)
        else:
            out.append((full, ext_len, ext_lba, False))
        off += rec_len


def main(iso_path):
    with open(iso_path, "rb") as f:
        pvd = read_sector(f, 16)
        if pvd[1:6] != b"CD001":
            print("ERROR: no CD001 signature at sector 16 -- not a valid ISO9660")
            return
        vol_id = pvd[40:72].decode("ascii", "replace").strip()
        vol_size = struct.unpack("<I", pvd[80:84])[0]
        root = pvd[156:190]
        root_lba = struct.unpack("<I", root[2:6])[0]
        root_len = struct.unpack("<I", root[10:14])[0]

        print("Volume ID : %s" % vol_id)
        print("Volume    : %d sectors (%.2f GB)" % (vol_size, vol_size * SECTOR / 1e9))
        print("Root LBA  : %d  len %d" % (root_lba, root_len))
        print()

        entries = []
        parse_dir(f, root_lba, root_len, "", entries)

    files = [e for e in entries if not e[3]]
    dirs = [e for e in entries if e[3]]
    total = sum(e[1] for e in files)
    print("%d files, %d directories, %.2f GB of file data" % (len(files), len(dirs), total / 1e9))
    print()

    by_ext = defaultdict(lambda: [0, 0])
    for path, size, lba, _ in files:
        ext = path.rsplit(".", 1)[-1].upper() if "." in path.rsplit("/", 1)[-1] else "(none)"
        by_ext[ext][0] += 1
        by_ext[ext][1] += size

    print("=== BY EXTENSION ===")
    for ext, (n, sz) in sorted(by_ext.items(), key=lambda kv: -kv[1][1]):
        print("  %-10s %5d files  %12s bytes  (%.1f MB)" % (ext, n, "{:,}".format(sz), sz / 1e6))
    print()

    print("=== 40 LARGEST FILES ===")
    for path, size, lba, _ in sorted(files, key=lambda e: -e[1])[:40]:
        print("  %12s  LBA %-9d %s" % ("{:,}".format(size), lba, path))
    print()

    with open(sys.argv[2], "w", encoding="utf-8") as out:
        out.write("path\tsize\tlba\n")
        for path, size, lba, is_dir in sorted(entries, key=lambda e: -e[1]):
            if not is_dir:
                out.write("%s\t%d\t%d\n" % (path, size, lba))
    print("full listing written to %s" % sys.argv[2])


if __name__ == "__main__":
    main(sys.argv[1])
