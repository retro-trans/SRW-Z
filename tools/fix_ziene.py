# -*- coding: utf-8 -*-
"""ツィーネ・エスピオ is "Ziene Espio" - unify the robot library with everything else.

The same character was spelled three different ways on three screens:

    pilot status screen   "Tziine"        (COMPDATA name record)
    robot library         "Tsiine Espio"  (ZKN_RT, here)
    scene dialogue        "Ziene"         (STAGE)

The Akurasu wiki's Z Pilot Database - this project's naming baseline - spells
her "Ziene Espio", and the PILOT library (ZKN_PT rec409) already agreed:
CHFN "Ziene Espio", CHNN "Ziene". So the dialogue and the pilot library were
right and the other two were wrong; the COMPDATA record is fixed through
compdata_ui_left.json, and this fixes the robot library.

Two entries mention her: rec315 (Chaos Caper) and rec316 (Eliphas), each in
both DSCR and DSC2. "Ziene Espio" is one byte SHORTER than "Tsiine Espio", but
that is NOT enough on its own - banlz is content-dependent and rec315 first
recompressed to 385 against a 384-byte slot. See REPLACEMENTS for the byte.

Usage: fix_ziene.py <iso> [--dry-run]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
import zkn

RT_LBA, RT_SIZE = 1824000, 97 * 2048
TARGETS = (315, 316)

# The name is one byte shorter, but banlz is content-dependent and rec315
# recompressed to 385 against a 384-byte slot - shorter text can pack worse.
# The second pair buys the byte back in prose rather than by moving the record:
# "design line" is a literal rendering of デザインライン and reads better without.
REPLACEMENTS = [
    (b"Tsiine Espio", b"Ziene Espio"),
    (b"a feminine design line to suit her", b"a feminine design to suit her"),
]


def rebuild(rec, replacements):
    """Return a fresh compressed record with every replacement applied."""
    pl = zkn.payload_of(rec)
    p = zkn.deobf(pl)
    _magic, _kind, _ver, ch = zkn.parse(pl)
    body, hits = b"", 0
    for tag, _off, data in ch:
        if tag in zkn.SCALAR:
            continue
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data)
            for old, new in replacements:
                if old in data:
                    data = data.replace(old, new)
                    hits += 1
        body += tag.encode("latin1") + struct.pack("<I", len(data)) + data
    if not hits:
        return None, 0
    end = 32 + len(body)
    out = (p[0:16] + b"DSIZ" + struct.pack("<I", end - 24)
           + b"DATA" + struct.pack("<I", end - 32) + body)
    out += b"\x00" * ((-len(out)) % 16)
    pay = zkn.obf(out)
    hdr = struct.pack("<8I", 1, 32, 0, len(pay), len(pay), 0, 0, 0)
    return banlz.compress_record_optimal(hdr + pay), hits


def main():
    iso, dry = sys.argv[1], "--dry-run" in sys.argv
    f = open(iso, "rb" if dry else "r+b")
    f.seek(RT_LBA * 2048)
    arch = bytearray(f.read(RT_SIZE))
    recs = banlz.decompress_all(bytes(arch))
    offs = [o for o, _d in recs]
    total = 0
    for idx in TARGETS:
        blob, hits = rebuild(bytes(recs[idx][1]), REPLACEMENTS)
        if blob is None:
            print("rec%-4d nothing to replace - already applied?" % idx)
            continue
        slot = offs[idx + 1] - offs[idx]
        if len(blob) > slot:
            print("rec%-4d REFUSED: %d bytes > slot %d" % (idx, len(blob), slot))
            return 1
        print("rec%-4d %d chunk(s) rewritten, %d bytes (slot %d)"
              % (idx, hits, len(blob), slot))
        arch[offs[idx]:offs[idx] + len(blob)] = blob
        for i in range(offs[idx] + len(blob), offs[idx + 1]):
            arch[i] = 0
        total += hits
    after = banlz.decompress_all(bytes(arch))
    assert [o for o, _d in after] == offs, "record offsets moved - refusing"
    for idx in TARGETS:
        _m, _k, _v, ch = zkn.parse(zkn.payload_of(bytes(after[idx][1])))
        for tag, _o, data in ch:
            if tag == "DSCR" and isinstance(data, (bytes, bytearray)):
                print("   rec%-4d %s" % (idx, bytes(data)[:64]
                                         .decode("cp932", "replace")
                                         .replace("\n", " | ")))
    if dry:
        print("dry run - nothing written")
        return 0
    f.seek(RT_LBA * 2048)
    f.write(bytes(arch))
    f.close()
    print("ZKN_RT rewritten at LBA %d, %d chunk(s) changed" % (RT_LBA, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
