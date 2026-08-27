# -*- coding: utf-8 -*-
"""Restore speaker lines that were emptied, leaving the box blank.

Reported from a screenshot 2026-08-26: the ~Atlandia~ location card before
Johannes's first line rendered as a completely empty box, and its backlog entry
was blank too.

    JP  '\\u3000\\n\\u3000...～アトランディア～'   speaker line = fullwidth space
    EN  '\\n            ~Atlandia~'          speaker line GONE, opens with 0x0A

A row is `speaker\\nbody`. Location cards and narration carry a fullwidth space
(sometimes two) as the speaker so that no name is drawn but the line still
exists. The translation dropped it on 20 rows, so those rows begin with the
newline and the renderer produces nothing at all.

scan_visible_defects.py checks for an empty BODY, never an empty speaker line,
so the whole class was invisible - see tools/scan_empty_speaker.py.

The fix is not invented: each row is given back exactly the leading whitespace
its OWN japanese source had, resolved through the pointer. Body text is
untouched. Rows that no longer fit their slot are appended and repointed, the
same mechanism as fix_truncated_rows.py.

Usage: fix_empty_speaker.py <iso> [--write]
"""
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())

    edited, inplace, reloc, bad, skipped = {}, 0, 0, [], []
    for idx in range(len(items)):
        e, j = items[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        eb = bytearray(e)
        jb = bytes(j)
        seen = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in seen:
                seen[ve] = vj
        for eo in sorted(seen, reverse=True):
            if eb[eo:eo + 1] != b"\n":
                continue
            jo = seen[eo]
            ze = bytes(eb).find(b"\x00", eo)
            zj = jb.find(b"\x00", jo)
            if ze <= eo or zj <= jo:
                continue
            try:
                se = bytes(eb[eo:ze]).decode("cp932")
                sj = jb[jo:zj].decode("cp932")
            except Exception:
                continue
            if sj.startswith("\n"):
                continue                       # japanese had none either
            lead = sj.split("\n", 1)[0]
            if lead.strip():
                # Not a location card. These are CONTINUATION FRAGMENTS: the
                # pointer addresses the middle of a longer line (both japanese
                # sources start on a cp932 trail byte), so the leading newline
                # is a real line break and must stay. Skip, do not fail.
                skipped.append((idx, eo, lead[:20]))
                continue
            new = lead + se
            # Only the speaker line changes. Do NOT re-validate the body: seven
            # of these location cards are ALREADY wider than 34 columns in the
            # shipped image (seven fullwidth spaces plus a long name), which is
            # a separate pre-existing defect. Rejecting them here would refuse
            # to fix a blank box because of a fault this pass does not touch.
            if new.split("\n")[1:] != se.split("\n")[1:]:
                bad.append((idx, eo, "body changed - refusing"))
                continue
            nb = new.encode("cp932")
            k = ze
            while k < len(eb) and eb[k] == 0:
                k += 1
            print("rec%-4d %#08x  %r -> %r"
                  % (idx, eo, se.replace("\n", " | ")[:44],
                     new.replace("\n", " | ")[:46]))
            if len(nb) < k - eo:
                eb[eo:k] = nb + b"\x00" * (k - eo - len(nb))
                inplace += 1
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op = struct.pack("<I", BASE + eo)
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
                    bad.append((idx, eo, "no pointer to repoint"))
                    continue
                for x in range(eo, k):
                    eb[x] = 0
                reloc += 1
            edited[idx] = bytes(eb)

    print("\nrows fixed: %d in place, %d relocated | rejected %d"
          % (inplace, reloc, len(bad)))
    for b in bad:
        print("   REJECT rec%-4d %#08x %s" % b)
    print("records to rebuild: %d" % len(edited))
    if not write or not edited or bad:
        if bad:
            print("\nREFUSING to write while any row is rejected")
        elif not write:
            print("\n(dry run - pass --write to apply)")
        return

    for idx, plain in edited.items():
        hdr = items[idx][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        blob = banlz.compress_record(plain)
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(plain)
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        print("   rec%-4d %d bytes (slot %d)" % (idx, len(blob), nxt - hdr))
        sys.stdout.flush()
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    chk = banlz.decompress_all(bytes(raw))
    for idx, plain in edited.items():
        assert bytes(chk[idx][1]) == plain, "readback mismatch rec %d" % idx
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("written and verified")


if __name__ == "__main__":
    main()
