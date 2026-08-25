# -*- coding: utf-8 -*-
"""Extract a member from a PCSX2 save state (.p2s).

PCSX2 stores its zip members with Zstandard (method 93), which Python's zipfile
refuses ("compression method is not supported"). Read the local file header
ourselves and decompress with the zstandard module.

Usage: p2s_extract.py <state.p2s> [member] [outfile]
       default member = eeMemory.bin
"""
import os
import struct
import sys
import zipfile

import zstandard


def extract(p2s, member, out):
    z = zipfile.ZipFile(p2s)
    info = z.getinfo(member)
    f = open(p2s, "rb")
    f.seek(info.header_offset)
    sig, ver, flag, method, mt, md, crc, csize, usize, nlen, elen = \
        struct.unpack("<IHHHHHIIIHH", f.read(30))
    if sig != 0x04034B50:
        raise SystemExit("bad local header")
    f.seek(nlen + elen, os.SEEK_CUR)
    comp = f.read(info.compress_size)
    f.close()

    if method == 93:                       # Zstandard
        data = zstandard.ZstdDecompressor().decompress(
            comp, max_output_size=info.file_size)
    elif method == 8:
        import zlib
        data = zlib.decompress(comp, -15)
    elif method == 0:
        data = comp
    else:
        raise SystemExit("unhandled method %d" % method)

    open(out, "wb").write(data)
    print("%s -> %s (%d bytes, method %d)"
          % (member, out, len(data), method))
    return data


def main():
    p2s = sys.argv[1]
    member = sys.argv[2] if len(sys.argv) > 2 else "eeMemory.bin"
    out = sys.argv[3] if len(sys.argv) > 3 else member
    extract(p2s, member, out)


if __name__ == "__main__":
    main()
