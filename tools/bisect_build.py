# -*- coding: utf-8 -*-
"""Build a CHD that is the VIRGIN japanese disc plus a chosen set of our files.

For a crash that reproduces on every build back to v0.8.1.1, "which of my
recent edits did this" is the wrong question - the right one is "which of the
twenty files we touch does the game choke on". This splices our version of a
named subset onto a clean japanese image, so a single playthrough halves the
search space instead of testing one file at a time.

The ELF is included in every set by default: our text uses private SJIS codes
that only the patched ELF renders, so a data-only image would be testing a
combination that has never existed.

    bisect_build.py TEXT   -> out/BISECT-TEXT.chd
    bisect_build.py ART
    bisect_build.py STAGE SRVC        (any explicit region names)
    bisect_build.py --list

Usage: bisect_build.py <group|region...> [-o NAME] [--no-elf]
"""
import io
import os
import shutil
import subprocess
import sys

SEC = 2048
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.dirname(ROOT)
JP = os.path.join(ROOT, "iso", "srwz.bin")
OURS = os.path.join(ROOT, "iso", "srwz_cap.bin")
CHDMAN = os.path.join(ROOT, "tools", "chdman.exe")

# name -> (lba, size)  every region where our build differs from the virgin disc
REGIONS = {
    "OP0":      (1312162, 266224),   "OP1":      (1312292, 265872),
    "OP2":      (1312422, 266352),   "SRVC":     (1313214, 3313040),
    "SRVC_SEG": (1309609, 1416),     "HSFC":     (1568541, 250112),
    "JTIM":     (1568664, 7539728),  "ZKN_KW":   (1573442, 29936),
    "ZKN_PT":   (1573457, 293696),   "ZKN_RT":   (1573601, 185600),
    "MTV_PROS": (1573437, 9056),     "NISVDATA": (1568269, 555056),
    "STAGE":    (1651029, 3910128),  "VT1":      (1588772, 127500736),
    "DMY":      (1765044, 122558928), "KVMDATA": (1289810, 3335408),
    "MAPMODEL": (1652964, 55136688), "MAPNAME":  (1652939, 49920),
    "ELF":      (455, 3471624),      "VMAP":     (450, 3072),
}
# DMY carries the RELOCATED files (COMPDATA and friends), so it is data, not
# padding - it belongs with TEXT even though its name suggests otherwise.
GROUPS = {
    "TEXT": ["SRVC", "SRVC_SEG", "STAGE", "HSFC", "ZKN_KW", "ZKN_PT",
             "ZKN_RT", "MTV_PROS", "MAPNAME", "DMY", "VMAP"],
    "ART":  ["OP0", "OP1", "OP2", "JTIM", "NISVDATA", "VT1", "KVMDATA",
             "MAPMODEL"],
}


def main():
    # Drop the VALUE that follows -o as well as the flag itself. It does not
    # start with "-", so a plain filter swept it into the region list and the
    # build died with "unknown region(s): ELFONLY" instead of honouring -o.
    argv = sys.argv[1:]
    args = []
    skip = False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "-o":
            skip = True
            continue
        if not a.startswith("-"):
            args.append(a)
    if "--list" in sys.argv or not args:
        print("groups : %s" % ", ".join(sorted(GROUPS)))
        print("regions: %s" % ", ".join(sorted(REGIONS)))
        return 0
    want = []
    for a in args:
        want += GROUPS[a.upper()] if a.upper() in GROUPS else [a.upper()]
    if "--no-elf" not in sys.argv and "ELF" not in want:
        want.append("ELF")
    bad = [w for w in want if w not in REGIONS]
    if bad:
        raise SystemExit("unknown region(s): %s" % ", ".join(bad))

    name = (sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv
            else "-".join(a.upper() for a in args))
    out = os.path.join(WORK, "SRWZ BISECT-%s.chd" % name)
    tmp = os.path.join(ROOT, "iso", "_bisect.bin")
    cue = os.path.join(ROOT, "iso", "_bisect.cue")

    print("virgin japanese + %d region(s): %s" % (len(want), ", ".join(want)))
    shutil.copyfile(JP, tmp)
    src = open(OURS, "rb")
    dst = open(tmp, "r+b")
    for w in want:
        lba, size = REGIONS[w]
        src.seek(lba * SEC)
        dst.seek(lba * SEC)
        left = size
        while left > 0:
            n = min(1 << 23, left)
            dst.write(src.read(n))
            left -= n
        print("   spliced %-9s %10d B at LBA %d" % (w, size, lba))
    src.close()
    dst.close()
    io.open(cue, "w", newline="\n").write(
        'FILE "_bisect.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')
    print("building %s ..." % os.path.basename(out))
    subprocess.run([CHDMAN, "createcd", "-i", cue, "-o", out, "-f"],
                   check=True, capture_output=True)
    os.remove(tmp)
    os.remove(cue)
    print("done: %s (%.2f GB)" % (out, os.path.getsize(out) / 2.0 ** 30))
    return 0


if __name__ == "__main__":
    sys.exit(main())
