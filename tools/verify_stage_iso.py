"""Read STAGE.BIN back out of the patched ISO, decompress record 1, and
confirm the English script is live."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
iso = open(sys.argv[1], "rb")
iso.seek(1651029 * SECTOR)
stage = iso.read(3910128)
iso.close()

total, flags, at = banlz.parse_header(stage, 0x00D860)
data, _ = banlz.decompress_stream(stage, at, total)
print("record 1 from ISO: %s bytes decompressed" % "{:,}".format(len(data)))

for probe in (b'Denzel\n"1:15 from scramble',
              b'Toby\n"A skirted knockoff',
              b'Quattro\n"Rough, but it moves well',
              b'Kamille\n"You order-taking drone!',
              b"Glory Star 1",
              b"Defeat Apolly & Roberto."):
    print("  %-42s %s" % (probe.decode(), "FOUND" if probe in data else "MISSING"))

# no Japanese should remain in the dialogue region (indexes 7..305 span)
jp = sum(1 for i in range(0x5700, 0xB300)
         if 0x81 <= data[i] <= 0x9F)
print("\nresidual SJIS lead bytes in dialogue region: %d" % jp)
