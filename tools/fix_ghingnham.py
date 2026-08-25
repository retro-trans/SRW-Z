# -*- coding: utf-8 -*-
"""ゲンガナム is "Ghingnham", not "Gendarme".

The keyword bank called entry #14 "Gendarme", but it is the Moon dome city
from Turn A Gundam - the entry's OWN description says "built by the Ghingnham
family", and the dialogue calls it the Ghingnham. Gendarme (ジャンダルム) is a
different word entirely.

Renames the bank WORD and the description's first word. The payload goes from
624 to 640 bytes against a 672-byte Japanese cap, so it stays strictly under
(see 0.8.63 for why "at the cap" is not good enough).

Usage: fix_ghingnham.py <iso>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
import zkn

KW_LBA, KW_SIZE = 1823200, 32768
IDX = 14


def main():
    iso_path = sys.argv[1]
    f = open(iso_path, "r+b")
    f.seek(KW_LBA * 2048)
    arch = bytearray(f.read(KW_SIZE))
    recs = banlz.decompress_all(bytes(arch))
    offs = [o for o, d in recs]
    rec = bytes(recs[IDX][1])
    pl = zkn.payload_of(rec)
    p = zkn.deobf(pl)
    magic, kind, ver, ch = zkn.parse(pl)
    cd = dict((c[0], c[2]) for c in ch)
    assert cd["WORD"].split(b"\x00")[0] == b"Gendarme", cd["WORD"]

    body = b""
    for tag, off, data in ch:
        if tag in zkn.SCALAR:
            continue
        if tag == "WORD":
            data = b"Ghingnham" + data[len(b"Gendarme"):]
        elif tag in ("DSCR", "DSC2") and data.startswith(b" Gendarme "):
            data = b" Ghingnham " + data[len(b" Gendarme "):]
        body += tag.encode("latin1") + struct.pack("<I", len(data)) + data
    end = 32 + len(body)
    out = (p[0:16] + b"DSIZ" + struct.pack("<I", end - 24)
           + b"DATA" + struct.pack("<I", end - 32) + body)
    out += b"\x00" * ((-len(out)) % 16)
    pay = zkn.obf(out)
    hdr = struct.pack("<8I", 1, 32, 0, len(pay), len(pay), 0, 0, 0)
    blob = banlz.compress_record_optimal(hdr + pay)

    slot = offs[IDX + 1] - offs[IDX]
    assert len(blob) <= slot, "blob %d > slot %d" % (len(blob), slot)
    arch[offs[IDX]:offs[IDX] + len(blob)] = blob
    for i in range(offs[IDX] + len(blob), offs[IDX + 1]):
        arch[i] = 0
    after = banlz.decompress_all(bytes(arch))
    assert [o for o, d in after] == offs, "record offsets moved"
    m, k, v, ch2 = zkn.parse(zkn.payload_of(bytes(after[IDX][1])))
    cd2 = dict((c[0], c[2]) for c in ch2)
    print("WORD: %r" % cd2["WORD"].split(b"\x00")[0].decode("cp932"))
    print("DSCR: %s" % cd2["DSCR"].decode("cp932")[:60].replace("\n", " | "))
    print("payload %d bytes (cap 672)" % len(zkn.payload_of(bytes(after[IDX][1]))))
    f.seek(KW_LBA * 2048)
    f.write(bytes(arch))
    f.close()
    print("bank updated; ELF offset table untouched (no record moved)")


if __name__ == "__main__":
    main()
