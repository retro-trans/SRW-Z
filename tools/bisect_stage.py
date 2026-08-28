# -*- coding: utf-8 -*-
"""Revert chosen STAGE records to the last-good build, inside the crashing one.

v1.54 clears the end of stage 1; v1.55 does not, and the only region that
matters is STAGE (confirmed by splicing: v1.54 + v1.55's STAGE crashes, v1.54
+ v1.55's DMY/ELF/KVMDATA/VMAP does not). 166 of 205 records changed between
them, so the question is which one.

Reverting is the right direction rather than porting forward: v1.54's records
are SMALLER than v1.55's (the text grew), so a reverted record always fits the
slot it is going back into, and every other record keeps its exact bytes and
offsets. Nothing moves, so nothing needs repointing.

    bisect_stage.py 13            revert record 13
    bisect_stage.py 0-99          revert a range
    bisect_stage.py 13 0 -o R13R0

Base image is the v1.55-STAGE bisect build, so the ONLY difference from the
crashing image is the records named here.

Usage: bisect_stage.py <index|a-b> [...] [-o NAME]
"""
import io
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.dirname(ROOT)
GOOD = os.path.join(ROOT, "iso", "_b154.bin")     # v1.54
BAD = os.path.join(ROOT, "iso", "_b155.bin")      # v1.54 + v1.55 STAGE
CHDMAN = os.path.join(ROOT, "tools", "chdman.exe")


def main():
    argv = sys.argv[1:]
    skip = argv.index("-o") + 1 if "-o" in argv else -1
    args = [a for i, a in enumerate(argv)
            if not a.startswith("-") and i != skip]
    if not args:
        raise SystemExit(__doc__)
    want = []
    for a in args:
        if "-" in a:
            lo, hi = a.split("-")
            want += list(range(int(lo), int(hi) + 1))
        else:
            want.append(int(a))
    want = sorted(set(want))
    name = (sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv
            else "REV" + args[0].replace("-", "to"))

    g = open(GOOD, "rb"); g.seek(LBA * SEC); graw = g.read(SIZE); g.close()
    b = open(BAD, "rb"); b.seek(LBA * SEC); braw = bytearray(b.read(SIZE)); b.close()
    good = banlz.decompress_all(graw)
    bad = banlz.decompress_all(bytes(braw))
    heads = sorted(h for h, _ in bad)

    for idx in want:
        plain = bytes(good[idx][1])
        hdr = bad[idx][0]
        nxt = min([h for h in heads if h > hdr] or [SIZE])
        blob = banlz.compress_record(plain)
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(plain)
        if len(blob) > nxt - hdr:
            raise SystemExit("rec %d does not fit its slot (%d > %d)"
                             % (idx, len(blob), nxt - hdr))
        braw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            braw[i] = 0
        print("   reverted rec %-4d  %d bytes into a %d-byte slot"
              % (idx, len(blob), nxt - hdr))

    check = banlz.decompress_all(bytes(braw))
    assert len(check) == len(bad), "record count changed"
    for i in range(len(check)):
        exp = good[i][1] if i in want else bad[i][1]
        assert bytes(check[i][1]) == bytes(exp), "rec %d is not what we meant" % i
    print("verified: %d reverted, %d untouched" % (len(want), len(check) - len(want)))

    tmp = os.path.join(ROOT, "iso", "_bstage.bin")
    cue = os.path.join(ROOT, "iso", "_bstage.cue")
    import shutil
    shutil.copyfile(BAD, tmp)
    f = open(tmp, "r+b"); f.seek(LBA * SEC); f.write(bytes(braw)); f.close()
    io.open(cue, "w", newline="\n").write(
        'FILE "_bstage.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')
    out = os.path.join(WORK, "SRWZ BISECT-%s.chd" % name)
    r = subprocess.run([CHDMAN, "createcd", "-i", cue, "-o", out, "-f"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit((r.stderr or r.stdout)[-400:])
    os.remove(tmp); os.remove(cue)
    print("built %s (%.2f GB)" % (os.path.basename(out),
                                  os.path.getsize(out) / 2.0 ** 30))


if __name__ == "__main__":
    main()
