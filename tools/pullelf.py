"""Find and extract the boot ELF (SLPS_xxxxx / the SYSTEM.CNF BOOT2 target)
from a PS2 ISO. Reuses the ISO9660 walker approach from isolist.py.
"""
import sys
import struct

SECTOR = 2048


def read_sector(f, lba, count=1):
    f.seek(lba * SECTOR)
    return f.read(SECTOR * count)


def walk(f, lba, size, path, out, depth=0):
    if depth > 8:
        return
    data = read_sector(f, lba, max(1, (size + SECTOR - 1) // SECTOR))
    off = 0
    while off < len(data):
        rlen = data[off]
        if rlen == 0:
            off = (off // SECTOR + 1) * SECTOR
            if off >= len(data):
                break
            continue
        rec = data[off:off + rlen]
        if len(rec) < 33:
            break
        ext_lba = struct.unpack("<I", rec[2:6])[0]
        ext_len = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen]
        if not (nlen == 1 and name in (b"\x00", b"\x01")):
            nm = name.decode("ascii", "replace").split(";")[0]
            full = path + "/" + nm
            if flags & 0x02:
                walk(f, ext_lba, ext_len, full, out, depth + 1)
            else:
                out.append((full, ext_len, ext_lba))
        off += rlen


def main(iso, outdir):
    import os
    os.makedirs(outdir, exist_ok=True)
    with open(iso, "rb") as f:
        pvd = read_sector(f, 16)
        assert pvd[1:6] == b"CD001", "not ISO9660"
        vol = pvd[40:72].decode("ascii", "replace").strip()
        root = pvd[156:190]
        rlba = struct.unpack("<I", root[2:6])[0]
        rlen = struct.unpack("<I", root[10:14])[0]
        print("Volume ID: %s" % vol)
        entries = []
        walk(f, rlba, rlen, "", entries)

        # SYSTEM.CNF names the boot ELF; also grab any SLPS/SLUS/SCPS file.
        elfs = [e for e in entries
                if "/SLPS" in e[0].upper() or "/SLUS" in e[0].upper()
                or "/SCPS" in e[0].upper() or e[0].upper().endswith(".ELF")]
        syscnf = [e for e in entries if e[0].upper().endswith("SYSTEM.CNF")]
        if syscnf:
            p, sz, lba = syscnf[0]
            f.seek(lba * SECTOR)
            print("\n--- SYSTEM.CNF ---")
            print(f.read(sz).decode("ascii", "replace"))

        print("\nboot ELF candidates:")
        for p, sz, lba in elfs:
            print("  %-24s %s bytes  LBA %d" % (p, "{:,}".format(sz), lba))
            flat = p.lstrip("/").replace("/", "_")
            f.seek(lba * SECTOR)
            open(os.path.join(outdir, flat), "wb").write(f.read(sz))
            print("     -> extracted to %s/%s" % (outdir, flat))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
