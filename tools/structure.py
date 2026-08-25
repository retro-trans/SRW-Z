"""Work out how a text file is structured: pointer table, fixed records, or
null-terminated stream. This decides how hard reinsertion will be.
"""
import sys
import struct
from collections import Counter


def hexdump(data, off, length=128):
    out = []
    for i in range(off, min(off + length, len(data)), 16):
        chunk = data[i:i + 16]
        hx = " ".join("%02X" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("  %08X  %-47s  %s" % (i, hx, asc))
    return "\n".join(out)


def check_pointer_table(data, n=64):
    """If the file opens with a pointer table, the first words will be
    ascending offsets that land inside the file."""
    print("=== FIRST %d 32-bit LE WORDS ===" % n)
    vals = []
    for i in range(n):
        if (i + 1) * 4 > len(data):
            break
        v = struct.unpack("<I", data[i * 4:(i + 1) * 4])[0]
        vals.append(v)
    for i in range(0, len(vals), 8):
        print("  [%04d] %s" % (i, " ".join("%08X" % v for v in vals[i:i + 8])))

    in_range = sum(1 for v in vals if 0 < v < len(data))
    ascending = sum(1 for a, b in zip(vals, vals[1:]) if b > a)
    print("\n  %d/%d values fall inside the file" % (in_range, len(vals)))
    print("  %d/%d are ascending" % (ascending, len(vals) - 1))
    if in_range > len(vals) * 0.8 and ascending > (len(vals) - 1) * 0.8:
        print("  --> LOOKS LIKE A POINTER TABLE")
        return vals
    print("  --> does not look like a leading pointer table")
    return None


def record_stride(offsets, top=8):
    """Find the most common gap between text runs -- a dominant gap means
    fixed-size records."""
    gaps = Counter()
    for a, b in zip(offsets, offsets[1:]):
        gaps[b - a] += 1
    print("\n=== MOST COMMON GAPS BETWEEN TEXT RUNS ===")
    for gap, count in gaps.most_common(top):
        print("  gap %6d bytes : %6d times" % (gap, count))
    return gaps


def main(path):
    with open(path, "rb") as f:
        data = f.read()
    print("FILE: %s  (%s bytes)\n" % (path, "{:,}".format(len(data))))
    print("=== HEAD ===")
    print(hexdump(data, 0, 256))
    print()
    check_pointer_table(data)

    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from sjisscan import find_runs
    runs = find_runs(data, min_chars=4)
    offs = [o for o, _ in runs]
    if offs:
        print("\n=== TEXT SPAN ===")
        print("  first run at 0x%08X, last at 0x%08X" % (offs[0], offs[-1]))
        print("  %d runs" % len(offs))
        record_stride(offs)
        print("\n=== CONTEXT AROUND FIRST TEXT RUN ===")
        print(hexdump(data, max(0, offs[0] - 48), 176))

        # Does some 32-bit word in the header point at the first string?
        print("\n=== SEARCHING HEADER FOR A POINTER TO THE FIRST STRING ===")
        target = offs[0]
        found = False
        for cand in range(max(0, target - 8), target + 2):
            needle = struct.pack("<I", cand)
            pos = data[:target].find(needle)
            while pos != -1:
                print("  value 0x%X (string start) referenced at header offset 0x%X" % (cand, pos))
                found = True
                pos = data[:target].find(needle, pos + 1)
        if not found:
            print("  no direct absolute pointer found -- offsets are likely relative to a base")


if __name__ == "__main__":
    main(sys.argv[1])
