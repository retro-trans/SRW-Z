# -*- coding: utf-8 -*-
"""Replace a byte sequence inside a ZKN encyclopedia archive, record in place.

The library data is banlz-compressed AND obfuscated, so a byte-level pass over
the disc cannot reach it - the same reason rename_term.py exists for STAGE. A
character renamed in the dialogue and in COMPDATA will still be spelled the old
way in the encyclopedia unless it is renamed here too. That is exactly how
"Tsiine Espio" survived in the robot library after the dialogue already said
Ziene, and how "Astonage" survived in the pilot library.

Each touched record is rebuilt chunk by chunk, re-obfuscated, recompressed and
written back inside its OWN slot. Record offsets are re-read afterwards and the
write is refused if any moved. banlz is content-dependent, so a replacement
that SHORTENS the text can still recompress larger than the slot (rec315 of
ZKN_RT went to 385 against 384) - the slot check is not a formality.

    zkn_rename.py <iso> --archive PT --from Astonage --to Astonaige [--dry-run]

Usage: zkn_rename.py <iso> --archive PT|RT|KW --from OLD --to NEW [--dry-run]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
import zkn
from fix_ziene import rebuild

ARCHIVES = {
    "KW": (1823200, 32768),
    "RT": (1824000, 97 * 2048),
    "PT": (1573457, 136 * 2048),
}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    iso = sys.argv[1]
    dry = "--dry-run" in sys.argv
    which = arg("--archive")
    old = arg("--from").encode("cp932")
    new = arg("--to").encode("cp932")
    if which not in ARCHIVES:
        raise SystemExit("--archive must be one of %s" % ", ".join(ARCHIVES))
    lba, size = ARCHIVES[which]

    f = open(iso, "rb" if dry else "r+b")
    f.seek(lba * 2048)
    arch = bytearray(f.read(size))
    recs = banlz.decompress_all(bytes(arch))
    offs = [o for o, _d in recs]

    targets = []
    for i, (_o, d) in enumerate(recs):
        if d is None:
            continue
        try:
            _m, _k, _v, ch = zkn.parse(zkn.payload_of(bytes(d)))
        except Exception:
            continue
        for _t, _off, data in ch:
            if isinstance(data, (bytes, bytearray)) and old in bytes(data):
                targets.append(i)
                break
    if not targets:
        print("ZKN_%s: no record contains %r - nothing to do" % (which, old))
        return 0
    print("ZKN_%s: %d record(s) contain %r" % (which, len(targets), old.decode()))

    total = 0
    for idx in targets:
        blob, hits = rebuild(bytes(recs[idx][1]), [(old, new)])
        slot = offs[idx + 1] - offs[idx]
        if len(blob) > slot:
            print("rec%-4d REFUSED: %d bytes > slot %d" % (idx, len(blob), slot))
            return 1
        print("rec%-4d %d chunk(s), %d bytes (slot %d)"
              % (idx, hits, len(blob), slot))
        arch[offs[idx]:offs[idx] + len(blob)] = blob
        for i in range(offs[idx] + len(blob), offs[idx + 1]):
            arch[i] = 0
        total += hits
    after = banlz.decompress_all(bytes(arch))
    if [o for o, _d in after] != offs:
        raise SystemExit("record offsets moved - refusing to write")
    for idx in targets:
        _m, _k, _v, ch = zkn.parse(zkn.payload_of(bytes(after[idx][1])))
        for t, _o, data in ch:
            if isinstance(data, (bytes, bytearray)) and new in bytes(data):
                print("   rec%-4d %-5s %s" % (idx, t, bytes(data)[:56]
                                              .decode("cp932", "replace")
                                              .replace("\n", " | ")))
    if dry:
        print("dry run - nothing written")
        return 0
    f.seek(lba * 2048)
    f.write(bytes(arch))
    f.close()
    print("ZKN_%s rewritten at LBA %d, %d chunk(s) changed" % (which, lba, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
