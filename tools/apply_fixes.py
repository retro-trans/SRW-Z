# -*- coding: utf-8 -*-
"""Splice proofreading fixes into the shipped image.

Input: analysis/review/fixes/recNNN_XXX.json - [{"row", "en"}]

Rows are located by RE-RESOLVING the pointer at apply time (script row ->
Japanese offset -> the pointer that references it -> where it lives in our
record now), never by a previously exported offset, because other passes
relocate rows and would desync a stale one.

Every fix is validated before anything is written: speaker line unchanged,
placeholder count unchanged, link markers unchanged and unsplit, body <= 3
lines of <= 34 columns with placeholders expanded, no fullwidth ellipsis. A
row that fails is reported and skipped, never forced.

Rows that outgrow their slot are relocated (append + repoint + zero).

Usage: apply_fixes.py <iso> [--dry-run]
"""
import glob
import io
import json
import multiprocessing
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(WORK, "analysis", "review", "fixes")
O, C = u"\u300a", u"\u300b"
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return cols(s)


SANITIZE = {u"—": "-", u"–": "-", u"‘": "'", u"’": "'",
            u"“": '"', u"”": '"', u"…": "...", u" ": " "}


def sanitize(s):
    """Agents write typographic characters cp932 has no room for."""
    for k, v in SANITIZE.items():
        s = s.replace(k, v)
    return s


RANK = {"Vice Admiral Edel": "General Edel", "Commodore Edel": "General Edel",
        "Colonel Edel": "General Edel", "Vice Admiral": "General",
        "Commodore": "General"}


def rebase(old, new):
    """Keep the CURRENT speaker line, take the agent's body.

    Agents are told not to touch the speaker line, but their copy of it goes
    stale the moment the naming pass renames a character. Rebasing makes a fix
    independent of that instead of rejecting it over a name it never chose.

    Also normalises 准将. The wiki has Edel Bernal as a Brigadier General of
    the New Earth Federation ARMY; agents each "standardised" her rank from
    their own slice and disagreed - Vice Admiral (which is 中将), Commodore,
    Colonel. In address, a brigadier general is called "General".
    """
    o, n = old.split(chr(10)), new.split(chr(10))
    if len(n) < 2:
        # A single-line fix has no speaker line. Falling back to the whole
        # string appends it AFTER the existing speaker and duplicates the
        # tail ("...」.」"). Refuse instead - validate() rejects the result.
        return None
    body = n[1:]
    out = chr(10).join([o[0]] + body)
    for k, v in RANK.items():
        out = out.replace(k, v)
    return out


def validate(old, new):
    o, n = old.split("\n"), new.split("\n")
    # A row with no kagi quote is not spoken dialogue: it is a glossary popup
    # description, an objective, or other MENU-drawn text, where ASCII 0x2E-0x3D
    # (. / 0-9 : ; < = ) are CONTROL CODES, so fullwidth punctuation and digits
    # are CORRECT there. Agents twice proposed "fixing" those to ASCII, which
    # would break rendering (the TypeDijeh bug). make_slices no longer sends
    # these rows out; this refuses any that slip through.
    if chr(0x300C) not in old:
        return "not spoken dialogue (menu-drawn row)"
    if o[0] != n[0]:
        return "speaker line changed"
    if len(n) - 1 > MAXLINES:
        return "%d body lines" % (len(n) - 1)
    for l in n[1:]:
        if ecols(l) > WIDTH:
            return "%d columns" % ecols(l)
        if l.count(O) != l.count(C):
            return "link split across lines"
    if u"\u2026" in new:
        return "fullwidth ellipsis"
    for k in EXPAND:
        if old.count(k) != new.count(k):
            return "placeholder %s count changed" % k
    if old.count(O) != new.count(O):
        return "link markers changed"
    return None


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    byrec = {}
    for p in sorted(glob.glob(os.path.join(FIX, "rec*.json"))):
        if p.endswith("_sonnet.json"):
            continue
        n = int(os.path.basename(p)[3:6])
        byrec.setdefault(n, []).extend(json.load(io.open(p, encoding="utf-8")))

    edited, ok, bad, reloc = {}, 0, [], 0
    for n, fixes in sorted(byrec.items()):
        script = json.load(io.open(os.path.join(
            WORK, "analysis", "rec%03d_script.json" % n), encoding="utf-8"))
        jb, eb = bytes(jp[n][1]), bytearray(items[n][1])
        ptr = {}
        for i in range(0, len(jb) - 4, 4):
            v = struct.unpack_from("<I", jb, i)[0] - BASE
            if 0 <= v < len(jb):
                ptr.setdefault(v, []).append(i)
        for fx in fixes:
            joff = script[fx["row"]].get("offset")
            if joff is None:
                bad.append((n, fx["row"], "no offset"))
                continue
            off = joff
            for p2 in ptr.get(joff, []):
                if p2 + 4 <= len(eb):
                    v = struct.unpack_from("<I", bytes(eb), p2)[0] - BASE
                    if 0 <= v < len(eb):
                        off = v
                        break
            e = off
            while e < len(eb) and eb[e] != 0:
                e += 1
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            try:
                old = bytes(eb[off:e]).decode("cp932")
            except UnicodeDecodeError:
                bad.append((n, fx["row"], "undecodable"))
                continue
            fx["en"] = rebase(old, sanitize(fx["en"]))
            if fx["en"] is None:
                bad.append((n, fx["row"], "single-line fix, no speaker line"))
                continue
            try:
                fx["en"].encode("cp932")
            except UnicodeEncodeError as ex:
                bad.append((n, fx["row"], "not cp932-encodable: %s" % ex.object[ex.start:ex.end]))
                continue
            why = validate(old, fx["en"])
            if why:
                bad.append((n, fx["row"], why))
                continue
            nb = fx["en"].encode("cp932")
            if len(nb) < k - off:
                eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            else:
                new_off = len(eb)
                eb += nb + b"\x00"
                op, npp = struct.pack("<I", BASE + off), struct.pack("<I", BASE + new_off)
                cnt, j = 0, 0
                while True:
                    j = eb.find(op, j)
                    if j < 0:
                        break
                    if j % 4 == 0:
                        eb[j:j + 4] = npp
                        cnt += 1
                        j += 4
                    else:
                        j += 1
                if cnt < 1:
                    del eb[new_off:]
                    bad.append((n, fx["row"], "no pointer to repoint"))
                    continue
                for x in range(off, k):
                    eb[x] = 0
                reloc += 1
            ok += 1
            edited[n] = bytes(eb)
    print("fixes applied %d (relocated %d) | rejected %d" % (ok, reloc, len(bad)))
    for b in bad[:12]:
        print("   rec %-4d row %-5d %s" % b)
    print("records to rebuild: %d" % len(edited))
    if dry or not edited:
        return

    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close(); pool.join()
    for n, plain in edited.items():
        hdr = items[n][0]
        blob = packed[n]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % n
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    # a re-run may leave a record byte-identical (its fixes are already in),
    # so assert containment rather than equality
    assert set(changed) <= set(items[n][0] for n in edited), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
