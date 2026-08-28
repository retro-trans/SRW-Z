# -*- coding: utf-8 -*-
"""Revert 「」 to ASCII quotes for a SLICE of rec 13's rows, and build a CHD.

Established by testing: reverting all of rec 13 to v1.54 clears the
end-of-stage-1 crash, and so does reverting just the 「」 quote marks in that
record. Not the glossary links, not row alignment, not width, not line count -
all four were tested and cleared. So the cause is inside the quote conversion,
and nothing in the data explains which row does it.

This narrows it by halves. Rows are indexed in offset order; --lo/--hi choose
the slice to revert, everything else keeps 「」.

    bisect_quotes.py --lo 0 --hi 118        first half
    bisect_quotes.py --lo 118 --hi 236      second half

The revert is byte-safe: 「 and 」 are two bytes and " is one, so a reverted
row only ever shrinks, and the freed bytes become NUL padding. No string
moves, no pointer changes, and every other record is verified byte-identical
before the image is packed.

Usage: bisect_quotes.py --lo N --hi N [-o NAME]
"""
import io
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from fix_popup_wrap import sstrings

SEC, LBA, SIZE, REC = 2048, 1651029, 3910128, 13
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.dirname(ROOT)
BASE = os.path.join(ROOT, "iso", "srwz_cap.bin")
CHDMAN = os.path.join(ROOT, "tools", "chdman.exe")
KO, KC = u"\u300c".encode("cp932"), u"\u300d".encode("cp932")


def main():
    lo = int(sys.argv[sys.argv.index("--lo") + 1]) if "--lo" in sys.argv else 0
    hi = int(sys.argv[sys.argv.index("--hi") + 1]) if "--hi" in sys.argv else 10 ** 9
    name = (sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv
            else "Q%d_%d" % (lo, hi))

    f = open(BASE, "rb"); f.seek(LBA * SEC); raw = bytearray(f.read(SIZE)); f.close()
    recs = banlz.decompress_all(bytes(raw))
    p = bytearray(recs[REC][1])
    hits = [(off, s) for off, s in sstrings(bytes(p)) if KO in s or KC in s]
    print("rec %d has %d rows with 「」; reverting index %d..%d"
          % (REC, len(hits), lo, min(hi, len(hits)) - 1))
    n = 0
    for i, (off, s) in enumerate(hits):
        if not (lo <= i < hi):
            continue
        new = s.replace(KO, b'"').replace(KC, b'"')
        p[off:off + len(s)] = new + b"\x00" * (len(s) - len(new))
        n += 1
    print("reverted %d rows" % n)

    hdr = recs[REC][0]
    heads = sorted(h for h, _ in recs)
    nxt = min([h for h in heads if h > hdr] or [SIZE])
    blob = banlz.compress_record(bytes(p))
    if len(blob) > nxt - hdr:
        blob = banlz.compress_record_optimal(bytes(p))
    if len(blob) > nxt - hdr:
        raise SystemExit("does not fit: %d > %d" % (len(blob), nxt - hdr))
    raw[hdr:hdr + len(blob)] = blob
    for i in range(hdr + len(blob), nxt):
        raw[i] = 0
    back = banlz.decompress_all(bytes(raw))
    assert bytes(back[REC][1]) == bytes(p)
    assert all(bytes(back[i][1]) == bytes(recs[i][1])
               for i in range(len(back)) if i != REC), "another record moved"
    print("verified: only rec %d changed" % REC)

    tmp = os.path.join(ROOT, "iso", "_bq.bin")
    cue = os.path.join(ROOT, "iso", "_bq.cue")
    shutil.copyfile(BASE, tmp)
    d = open(tmp, "r+b"); d.seek(LBA * SEC); d.write(bytes(raw)); d.close()
    io.open(cue, "w", newline="\n").write(
        'FILE "_bq.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')
    out = os.path.join(WORK, "SRWZ BISECT-%s.chd" % name)
    r = subprocess.run([CHDMAN, "createcd", "-i", cue, "-o", out, "-f"],
                       capture_output=True, text=True)
    os.remove(tmp); os.remove(cue)
    if r.returncode:
        raise SystemExit((r.stderr or r.stdout)[-300:])
    print("built %s (%.2f GB)" % (os.path.basename(out),
                                  os.path.getsize(out) / 2.0 ** 30))


if __name__ == "__main__":
    main()
