"""Convert a MODE1/2352 .bin track into a plain 2048-byte/sector .iso.

MODE1 sector layout (2352 bytes):
    [0:12]     sync pattern 00 FF*10 00
    [12:16]    header (min, sec, frame, mode)
    [16:2064]  user data (2048 bytes)   <- what we want
    [2064:]    EDC / ECC
"""
import sys

SECTOR = 2352
USER_OFF = 16
USER_LEN = 2048
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"


def convert(src, dst):
    bad_sync = 0
    sectors = 0
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            chunk = fi.read(SECTOR * 512)
            if not chunk:
                break
            out = bytearray()
            for off in range(0, len(chunk) - SECTOR + 1, SECTOR):
                sec = chunk[off:off + SECTOR]
                if sec[:12] != SYNC:
                    bad_sync += 1
                mode = sec[15]
                if mode != 1 and bad_sync < 5:
                    print("  warning: sector %d has mode %d" % (sectors, mode))
                out += sec[USER_OFF:USER_OFF + USER_LEN]
                sectors += 1
            fo.write(out)
            if sectors % 200000 < 512:
                print("  %d sectors..." % sectors)
    return sectors, bad_sync


if __name__ == "__main__":
    sectors, bad_sync = convert(sys.argv[1], sys.argv[2])
    print("done: %d sectors -> %d bytes" % (sectors, sectors * USER_LEN))
    print("sectors with unexpected sync: %d" % bad_sync)
