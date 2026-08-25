"""Raw hex + straight Shift-JIS decode of a region, to tell interleaved
binary apart from a decoder alignment bug."""
import sys

data = open(sys.argv[1], "rb").read()
off = int(sys.argv[2], 16)
ln = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x100

chunk = data[off:off + ln]
for i in range(0, len(chunk), 16):
    row = chunk[i:i + 16]
    print("  %08X  %-47s %s" % (
        off + i, " ".join("%02X" % b for b in row),
        "".join(chr(b) if 32 <= b < 127 else "." for b in row)))

print("\n--- straight shift_jis, errors=replace ---")
print(chunk.decode("shift_jis", errors="replace"))
