"""Dump a range of PCSX2 EE RAM via PINE to a file.  Usage:
    python pine_dump.py <hex_addr> <nbytes> <out.bin>
Reads in 32-bit words (op=2), batched, so any range works.
"""
import sys, struct
from pine_read import Pine


def main():
    addr = int(sys.argv[1], 16)
    n = int(sys.argv[2], 0)
    out = sys.argv[3]
    p = Pine()
    sys.stderr.write("connected via %s\n" % p.kind)
    words = (n + 3) // 4
    data = bytearray()
    CH = 256  # words per batch
    a = addr
    got = 0
    while got < words:
        k = min(CH, words - got)
        vals = p.read32_batch([a + i * 4 for i in range(k)])
        for v in vals:
            data += struct.pack("<I", v)
        a += k * 4
        got += k
    open(out, "wb").write(bytes(data[:n]))
    sys.stderr.write("wrote %d bytes from %#x -> %s\n" % (n, addr, out))


if __name__ == "__main__":
    main()
