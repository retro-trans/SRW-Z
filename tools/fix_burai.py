# -*- coding: utf-8 -*-
"""Fix 'Bry' - a fourth spelling of ブライ that the rename rules missed.

fix_terms_grow.py renames ブライ from Bray, Brya and Brai to Burai. It does not
cover "Bry", so 13 rows still read "Great Emperor Bry" (Getter Robo's 百鬼帝国
ruler, Emperor Burai). Reported from a screenshot 2026-08-26.

Every match is conditioned on the JAPANESE containing ブライ, resolved through
the row's pointer, so nothing unrelated is renamed - "Bry" could otherwise be a
prefix of a real word.

Burai is two bytes longer than Bry, so a row that no longer fits its slot is
appended to the record and repointed, the same mechanism as fix_truncated_rows.

Also fixes one speaker line: rec48 0x017a70 is attributed to "Burai" where the
japanese speaker is 風見 (Kazami). That is the speaker-taken-from-the-body bug
tools/scan_speaker_mismatch.py reports; here the body mentions 百鬼ブライ.

Usage: fix_burai.py <iso> [--write]
"""
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WIDTH, MAXLINES = 34, 3
BURAI_JP = u"ブライ"
SPEAKER_FIX = {(48, 0x017a70): ("Burai", "Kazami")}

# Burai is two columns wider than Bry, which pushes one single-line row over the
# 34-column limit. Re-wrap it rather than drop the fix.
NL = chr(10)
REWRAP = {
    (48, 0x017150): (u"Hyakuninshu" + NL + u"「Long live" + NL
                     + u"　Great Emperor Burai!!」"),
}


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

    edited, inplace, reloc, bad = {}, 0, 0, []
    for idx in range(len(items)):
        e, j = items[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        eb = bytearray(edited.get(idx, e))
        jb = bytes(j)
        ptr = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in ptr:
                ptr[ve] = vj
        for off in sorted(ptr, reverse=True):
            z = bytes(eb).find(b"\x00", off)
            if z <= off:
                continue
            try:
                s = bytes(eb[off:z]).decode("cp932")
            except Exception:
                continue
            jo = ptr[off]
            zj = jb.find(b"\x00", jo)
            src = jb[jo:zj].decode("cp932", "ignore") if zj > jo else ""
            new = s
            if BURAI_JP in src:
                new = re.sub(r"\bBry\b", "Burai", new)
            rw = REWRAP.get((idx, off))
            if rw is not None and new != s:
                new = rw
            sp = SPEAKER_FIX.get((idx, off))
            if sp and new.split("\n")[0] == sp[0]:
                new = sp[1] + new[len(sp[0]):]
            if new == s:
                continue
            body = new.split("\n")[1:]
            if len(body) > MAXLINES or any(cols(b) > WIDTH for b in body):
                bad.append((idx, off, "would not fit the box: %r" % new[:40]))
                continue
            nb = new.encode("cp932")
            k = z
            while k < len(eb) and eb[k] == 0:
                k += 1
            print("  rec%-4d %#08x %r" % (idx, off, new.replace("\n", " | ")[:64]))
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
                    bad.append((idx, off, "no pointer to repoint"))
                    continue
                for x in range(off, k):
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
