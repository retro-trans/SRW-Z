# -*- coding: utf-8 -*-
"""Reader/writer for the encyclopedia files (MTVZKNRT/PT/KW = 図鑑 robot /
character / keyword).

Format, finally cracked:
  file            = banlz archive, one record per entry
  record          = 32-byte header [1][0x20 dataoff][0][size][size][0,0,0]
                    followed by `size` bytes of payload
  payload         = XOR 0x5E, leaving 0x00 and 0x5E themselves unchanged
                    (that is why every plain-text search of the disc failed)
  decoded payload = 'ZKAN' + type ('ROBO'/'CHAR'/'KYWD') + u32 version
                    then a chunk stream: TAG(4) + u32 length + data

The two fixed points matter.  Skipping 0x00 keeps the cipher from injecting
NULs into NUL-terminated data; skipping 0x5E is what makes the map an
involution instead of a collision.  Get this wrong and it fails subtly rather
than loudly: plain XOR turns every structural 0x00 into 0x5E and corrupts the
length fields, while "skip 0x00 only" silently destroys every SJIS 'タ'
(0x83 0x5E) in the corpus - データ, マスター, スター - since 0x5E is both the
key and a legitimate trail byte.  Verified against raw bytes, not inferred.
"""
import struct

KEY = 0x5E
_MAP = bytes(c if c in (0x00, KEY) else c ^ KEY for c in range(256))


def deobf(b):
    """payload -> plaintext."""
    return bytes(b).translate(_MAP)


obf = deobf                    # the map is an involution


# Tags whose u32 is a VALUE, not a byte length (record-level header fields).
SCALAR = {"DSIZ", "DATA"}


def parse(payload):
    """Return (magic, kind, version, [(tag, offset_in_payload, data), ...]).

    Layout: 'ZKAN' + kind + version + nchunks, then the chunk stream
    TAG(4) + u32 len + len bytes.  DSIZ/DATA are scalar fields.
    """
    p = deobf(payload)
    magic, kind = p[0:4], p[4:8]
    ver = struct.unpack_from("<I", p, 8)[0]
    chunks = []
    i = 16
    while i + 8 <= len(p):
        tag = p[i:i + 4]
        if not all(0x20 <= c < 0x7F for c in tag):
            break
        val = struct.unpack_from("<I", p, i + 4)[0]
        name = tag.decode("latin1")
        if name in SCALAR:
            chunks.append((name, i + 4, val))
            i += 8
            continue
        if i + 8 + val > len(p):
            break
        chunks.append((name, i + 8, p[i + 8:i + 8 + val]))
        i += 8 + val
    return magic.decode("latin1"), kind.decode("latin1"), ver, chunks


def records(path):
    """Yield (index, record_bytes) for every entry in a ZKN file."""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import banlz
    d = open(path, "rb").read()
    recs = banlz.decompress_all(bytearray(d))
    for ri in range(len(recs)):
        dd, _ = banlz.decompress_record(d, recs[ri][0])
        yield ri, bytes(dd)


def payload_of(rec):
    size = struct.unpack_from("<I", rec, 0x0C)[0]
    return rec[0x20:0x20 + size]


if __name__ == "__main__":
    import sys, io
    path = sys.argv[1] if len(sys.argv) > 1 else \
        r"E:\Projects\SRW Z\_work\extracted\DATA_MTVZKNRT.BIN"
    out = io.open(sys.argv[2] if len(sys.argv) > 2 else "zkn_dump.txt", "w",
                  encoding="utf-8")
    n = 0
    from collections import Counter
    tags = Counter()
    for ri, rec in records(path):
        magic, kind, ver, chunks = parse(payload_of(rec))
        n += 1
        if ri < 4:
            out.write("=== record %d  %s/%s v%d  payload=%d ===\n"
                      % (ri, magic, kind, ver, len(payload_of(rec))))
            for tag, off, data in chunks:
                if isinstance(data, int):
                    out.write("   %-4s = %d\n" % (tag, data))
                    continue
                try:
                    t = data.decode("cp932").rstrip("\x00")
                except Exception:
                    t = "<%d bytes>" % len(data)
                out.write("   %-4s %4d @%05X  %s\n" % (tag, len(data), off, t[:200]))
        for tag, off, data in chunks:
            tags[tag] += 1
    out.write("\nrecords: %d\nchunk tags: %s\n" % (n, dict(tags)))
    out.close()
    print("records:", n, "tags:", dict(tags))
