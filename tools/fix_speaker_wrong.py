# -*- coding: utf-8 -*-
"""Fix rows attributed to the WRONG CHARACTER.

tools/scan_speaker_mismatch.py groups every row by its japanese speaker and
reports rows whose english label disagrees with its own group. The cause is
visible in rec53, where five consecutive ギンガナム lines are labelled
Ghingnham, Dianna and Agrippa: the wrong ones carry the first character NAMED IN
THE BODY, so a pass took the speaker from the sentence instead of the field.

Only the WRONG-CHARACTER half is fixed here. Rows whose label merely spells the
same character differently (Kiel/Kihel, Orba/Olba, Astonaji/Astonage) are left
alone - choosing between those is a naming decision that belongs to the akurasu
baseline, not to a majority vote. The two are separated by string similarity:
below 0.55 the labels are different people, above it they are spellings.

This is NOT majority-voting a name. The replacement is the label the rest of
that speaker's own rows already use, and every one of them matches a name
already established elsewhere in the project - Ghingnham is fix_terms_grow's
canonical form, Guin is Turn A's Guin Sard Lineford, and so on. What changes is
WHO is speaking, not how their name is spelt.

Left alone deliberately: the 9 rows whose japanese speaker is an ideographic
space and whose english is an ASCII space. Both render blank, there is no
report of a problem, and rewriting them risks the empty-speaker bug 0.8.85 fixed.

Usage: fix_speaker_wrong.py <iso> [--write]
"""
import hashlib
import json
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3
SKIP_JP = {u"　"}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    fixes = json.load(open("analysis/speaker_wrong.json", encoding="utf-8"))
    byrec = {}
    for x in fixes:
        if x["jp"] in SKIP_JP:
            continue
        byrec.setdefault(x["rec"], []).append(x)

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))

    edited, inplace, reloc, bad = {}, 0, 0, []
    for n in sorted(byrec):
        eb = bytearray(items[n][1])
        for x in sorted(byrec[n], key=lambda y: -y["off"]):
            off = x["off"]
            z = bytes(eb).find(b"\x00", off)
            if z <= off:
                continue
            try:
                s = bytes(eb[off:z]).decode("cp932")
            except Exception:
                continue
            if "\n" not in s:
                continue
            head, rest = s.split("\n", 1)
            if head != x["got"]:
                continue                      # already fixed, or moved
            new = x["want"] + "\n" + rest
            # Only the speaker line changes, so validate THAT, not the body: one
            # row (rec144 0x020850) is already wider than 34 columns in the
            # shipped image, and re-checking the body would refuse to fix its
            # speaker over a fault this pass does not touch.
            if new.split("\n")[1:] != s.split("\n")[1:]:
                bad.append((n, off, "body changed - refusing"))
                continue
            if cols(x["want"]) > WIDTH:
                bad.append((n, off, "speaker label too wide"))
                continue
            nb = new.encode("cp932")
            k = z
            while k < len(eb) and eb[k] == 0:
                k += 1
            if len(nb) < k - off:
                eb[off:k] = nb + b"\x00" * (k - off - len(nb))
                inplace += 1
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op = struct.pack("<I", BASE + off)
                npp = struct.pack("<I", BASE + new_off)
                cnt, q = 0, 0
                while True:
                    q = eb.find(op, q)
                    if q < 0:
                        break
                    if q % 4 == 0:
                        eb[q:q + 4] = npp
                        cnt += 1
                        q += 4
                    else:
                        q += 1
                if cnt < 1:
                    del eb[new_off:]
                    bad.append((n, off, "no pointer to repoint"))
                    continue
                for y in range(off, k):
                    eb[y] = 0
                reloc += 1
            edited[n] = bytes(eb)

    print("speaker labels corrected: %d in place, %d relocated | rejected %d"
          % (inplace, reloc, len(bad)))
    for b in bad[:8]:
        print("   REJECT rec%-4d %#08x %s" % b)
    print("records to rebuild: %d" % len(edited))
    if not write or not edited:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return

    for n, plain in edited.items():
        hdr = items[n][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        # Compressing 35 records outlives a single run, and a run that is cut
        # off writes nothing. Cache each result on disk keyed by the plain
        # record's sha1 so a re-run resumes instead of starting over.
        cdir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "analysis", "_lzcache")
        if not os.path.isdir(cdir):
            os.makedirs(cdir)
        key = os.path.join(cdir, "%s.lz" % hashlib.sha1(plain).hexdigest())
        if os.path.exists(key):
            blob = open(key, "rb").read()
        else:
            blob = banlz.compress_record(plain)
            if len(blob) > nxt - hdr:
                blob = banlz.compress_record_optimal(plain)
            open(key, "wb").write(blob)
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % n
        print("   rec%-4d %d bytes (slot %d)" % (n, len(blob), nxt - hdr))
        sys.stdout.flush()
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for n, plain in edited.items():
        assert bytes(chk[n][1]) == plain, "readback mismatch rec %d" % n
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")


if __name__ == "__main__":
    main()
