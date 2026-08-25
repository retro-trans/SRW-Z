# -*- coding: utf-8 -*-
"""Read PCSX2 save states (.p2s).

A .p2s is a ZIP whose members use compression method 93 (Zstandard), which
Python's zipfile cannot open - so pull the raw member bytes and inflate them
with the zstandard module directly.

Members include eeMemory.bin (32 MB of EE RAM, PS2 physical address 0 at file
offset 0) and Screenshot.png (the exact frame the state was taken on), which
together let us inspect what the game was actually doing at a moment we cannot
reproduce ourselves.

Usage: p2s.py <state.p2s> [member] [outfile]
       p2s.py <state.p2s> --list
"""
import struct
import sys
import zipfile

import zstandard


def read_member(path, name):
    """Return the decompressed bytes of one member."""
    zf = zipfile.ZipFile(path)
    info = zf.getinfo(name)
    with open(path, "rb") as f:
        f.seek(info.header_offset)
        sig, _, _, _, _, _, _, _, _, nlen, elen = struct.unpack("<IHHHHHIIIHH",
                                                                f.read(30))
        assert sig == 0x04034B50, "bad local header at %d" % info.header_offset
        f.seek(info.header_offset + 30 + nlen + elen)
        raw = f.read(info.compress_size)
    if info.compress_type == 93:
        return zstandard.ZstdDecompressor().decompress(
            raw, max_output_size=max(info.file_size, 1))
    return zf.read(name)


def ee(path):
    """EE main RAM: 32 MB, physical address N is byte N."""
    return read_member(path, "eeMemory.bin")


def main():
    p = sys.argv[1]
    if "--list" in sys.argv:
        for i in zipfile.ZipFile(p).infolist():
            print("%-30s %10d (method %d)" % (i.filename, i.file_size,
                                              i.compress_type))
        return
    name = sys.argv[2] if len(sys.argv) > 2 else "eeMemory.bin"
    data = read_member(p, name)
    if len(sys.argv) > 3:
        open(sys.argv[3], "wb").write(data)
        print("wrote %d bytes -> %s" % (len(data), sys.argv[3]))
    else:
        print("%s: %d bytes" % (name, len(data)))


if __name__ == "__main__":
    main()
