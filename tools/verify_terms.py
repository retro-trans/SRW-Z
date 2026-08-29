# -*- coding: utf-8 -*-
"""Fail the build if a spelling we already fixed has come back, ANYWHERE.

Two lessons are baked into this file; both cost a shipped defect.

1. A caption fix applied as a BYTE EDIT to the image does not survive.
   srvc_apply --free rebuilds every caption from analysis/srvc_en.json, so the
   next rebuild silently restores the old text. That is how 0.8.98 shipped 148
   regressed captions after they had been verified in the image.

2. THE GATE MUST LOOK EVERYWHERE THE TEXT LIVES. This file used to scan STAGE
   and SRVC only. The ENCYCLOPEDIA is a third surface - three banlz archives,
   XOR 0x5E, reached through zkn.py - and it was carrying 97 occurrences of
   spellings corrected builds earlier: Cherudim x38, Olson x37, Kaimera x10,
   Bry x6, Teraru x2, Afrodia, Raben. Every gate run had passed.

And a trap in the checking itself: 「 is 0x81 0x75, and 0x75 is ASCII 'u', a
WORD character. A \b regex over raw cp932 bytes therefore never matches a name
that opens a line of speech - it silently skips exactly the lines that matter
most. So this scans DECODED TEXT, never raw bytes.

Usage: verify_terms.py <iso>
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import zkn

SECTOR = 2048
STAGE = (1651029, 3910128)
SRVC = (1313214, 1618 * SECTOR)
ZKN_FILES = ("MTVZKNPT.BIN", "MTVZKNRT.BIN", "MTVZKNKW.BIN")

# spelling -> what it should be. Every one was fixed in a shipped build; if it
# reappears, something rebuilt from a stale source.
BANNED = {
    "Teraru": "Teral",
    "Kaimera": "Chimera",
    "Loewen": "Lowen", "Reeben": "Lowen", "Reuben": "Lowen",
    "Raeven": "Lowen", "Reeven": "Lowen", "Reben": "Lowen",
    "Reven": "Lowen", "Raben": "Lowen",
    "Olson": "Orson",
    "Afrodia": "Aphrodia",
    "Cherudim": "Cherubim",
    "Zeravair": "Zeravire",
    "Sylvia": "Silvia",
    "Bry": "Burai",
    # names settled against the SRW wiki, 0.8.106
    "Tetes": "Teteth",
    "Ze Edel": "The Edel",
    "Jee": "Jie",
    "Jay Babel": "Jie Babel",
}
# "Raven" and "Leben" are ordinary words and appear legitimately - a different
# character IS called Raven - so they are checked against the japanese by
# rename_term.py instead of banned outright here.


def strings_of(blob):
    """Every NUL-delimited run in a blob, decoded. Skips what will not decode."""
    for part in bytes(blob).split(b"\x00"):
        if len(part) < 2:
            continue
        try:
            yield part.decode("cp932")
        except UnicodeDecodeError:
            continue


def zkn_text(iso, name):
    """Pull one encyclopedia archive out of the image via the game file table."""
    f = open(iso, "rb")
    boot = f.read(0x120000)
    key = (chr(92) * 2 + "DATA" + chr(92) * 2 + name + ";1").encode()
    k = boot.find(key)
    if k < 0:
        f.close()
        return []
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    f.seek(lba * SECTOR)
    tmp = os.path.join(os.path.dirname(iso), "_zkn_gate.bin")
    open(tmp, "wb").write(f.read(nsec * SECTOR))
    f.close()
    out = []
    try:
        for _ri, rec in zkn.records(tmp):
            for c in zkn.parse(zkn.payload_of(rec))[3]:
                d = c[-1]
                if isinstance(d, (bytes, bytearray)):
                    try:
                        out.append(bytes(d).decode("cp932").rstrip("\x00"))
                    except UnicodeDecodeError:
                        pass
    finally:
        os.remove(tmp)
    return out


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(STAGE[0] * SECTOR)
    stage = banlz.decompress_all(f.read(STAGE[1]))
    f.seek(SRVC[0] * SECTOR)
    srvc = f.read(SRVC[1])
    f.close()

    surfaces = {"script": [], "captions": list(strings_of(srvc)),
                "encyclopedia": []}
    for _h, p in stage:
        if p is not None:
            surfaces["script"] += list(strings_of(bytes(p)))
    for name in ZKN_FILES:
        surfaces["encyclopedia"] += zkn_text(iso, name)

    bad = []
    for term, want in sorted(BANNED.items()):
        pat = re.compile(r"\b" + re.escape(term) + r"\b")
        counts = {k: sum(len(pat.findall(t)) for t in v)
                  for k, v in surfaces.items()}
        if any(counts.values()):
            bad.append((term, want, counts))
    if not bad:
        print("term gate OK: %d corrected spellings, none returned, across "
              "script + captions + encyclopedia" % len(BANNED))
        return 0
    print("REGRESSION: %d corrected spelling(s) are back" % len(bad))
    for term, want, c in bad:
        print("   %-10s should be %-12s script %3d  captions %3d  encyclopedia %3d"
              % (term, want, c["script"], c["captions"], c["encyclopedia"]))
    print("\nCaptions rebuild from analysis/srvc_en.json and the encyclopedia "
          "from analysis/zkn_en_round3.json - fix them THERE, not in the image.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
