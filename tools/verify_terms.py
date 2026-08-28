# -*- coding: utf-8 -*-
"""Fail the build if a spelling we already fixed has come back.

0.8.98 shipped with 148 captions regressed, and nothing noticed. The cause is
worth stating plainly, because it will happen again otherwise:

    A caption fix applied as a BYTE EDIT to the image does not survive.
    srvc_apply --free rebuilds every caption from analysis/srvc_en.json, so
    the next rebuild silently restores the old text.

Teraru->Teral, Kaimera->Chimera and the eleven spellings of レーベン were all
byte-edited in, all verified in the image at the time, and all quietly undone by
a later rebuild. The verification was real; it just measured something that was
about to be overwritten.

Caption corrections belong in analysis/srvc_en.json. This gate catches it when
they do not: it scans the FINISHED image for spellings that should no longer
exist anywhere, so a regression fails the build rather than reaching a player.

Add a term the moment you fix one. The cost of a wrong entry is a build that
stops; the cost of a missing one is a defect shipping twice.

Usage: verify_terms.py <iso>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR = 2048
STAGE = (1651029, 3910128)
SRVC = (1313214, 1618 * SECTOR)

# spelling -> what it should be. Every one of these was fixed in a shipped
# build; if it reappears, something rebuilt from a stale source.
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
}
# "Raven" and "Leben" are ordinary words and appear legitimately - a different
# character IS called Raven - so they are checked against the japanese by
# rename_term.py instead of banned outright here.


def main():
    iso = sys.argv[1]
    f = open(iso, "rb")
    f.seek(STAGE[0] * SECTOR)
    stage = b"".join(bytes(p) for _h, p in banlz.decompress_all(f.read(STAGE[1]))
                     if p is not None)
    f.seek(SRVC[0] * SECTOR)
    srvc = f.read(SRVC[1])
    f.close()

    bad = []
    for term, want in sorted(BANNED.items()):
        pat = re.compile(rb"\b" + term.encode() + rb"\b")
        ns, nc = len(pat.findall(stage)), len(pat.findall(srvc))
        if ns or nc:
            bad.append((term, want, ns, nc))
    if not bad:
        print("term gate OK: none of the %d corrected spellings have returned"
              % len(BANNED))
        return 0
    print("REGRESSION: %d corrected spelling(s) are back in the image" % len(bad))
    for term, want, ns, nc in bad:
        print("   %-10s should be %-10s script %4d  captions %4d"
              % (term, want, ns, nc))
    print("\nCaption text is rebuilt from analysis/srvc_en.json - fix it THERE, "
          "not in the image, or the next rebuild will undo it again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
