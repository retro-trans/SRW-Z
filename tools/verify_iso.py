"""Read the patched files back out of the ISO and confirm the English is there."""
import sys

SECTOR = 2048
iso = open(sys.argv[1], "rb")

print("=== /MAP/MAPNAME.BIN from the patched ISO ===")
iso.seek(1652939 * SECTOR)
mapname = iso.read(49920)
for i in list(range(0, 14)) + [32, 35, 37, 39, 53, 54, 55, 58, 59, 63]:
    base = i * 256
    end = mapname.find(b"\x00", base, base + 256)
    print("   [%3d] %s" % (i, mapname[base:end].decode("shift_jis", errors="replace")))

print("\n=== boot ELF strings from the patched ISO ===")
iso.seek(455 * SECTOR)
elf = iso.read(3471624)
for off in (0x00335E58, 0x00336928, 0x00336E88, 0x0033A0F8, 0x0033A130,
            0x0033A2E0, 0x0033A360, 0x0033ADB0, 0x0033AF50, 0x0033ABD0):
    end = elf.find(b"\x00", off)
    print("   0x%08X  %s" % (off, elf[off:end].decode("shift_jis", errors="replace")))

# the ISO9660 structures must be untouched
iso.seek(16 * SECTOR)
pvd = iso.read(2048)
print("\n=== filesystem integrity ===")
print("   PVD signature : %s" % ("CD001 OK" if pvd[1:6] == b"CD001" else "BROKEN"))
print("   Volume ID     : %s" % pvd[40:72].decode("ascii", "replace").strip())
iso.close()
