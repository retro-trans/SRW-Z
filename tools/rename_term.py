# -*- coding: utf-8 -*-
"""Rename a term everywhere in STAGE.BIN, conditioned on the japanese.

Every rename in this project has needed the same three things, so this does them
once instead of growing another one-off tool each time:

  * the row's JAPANESE must contain the source term, resolved through the row's
    own pointer. Without that a rename cannot be trusted - "Raven", "Lane" and
    "Leben" are all ordinary words as well as spellings of a character's name,
    and a blind search-and-replace hits real prose.
  * the result must still fit the box: 3 lines of 34 columns. A row that was
    ALREADY over-width in the shipped image is not this pass's fault, so it is
    only rejected when this pass makes it worse.
  * a row that no longer fits its slot is appended to the record and repointed
    rather than dropped.

STAGE is banlz-compressed, which is why a byte-level pass over the disc cannot
reach it: fix_srvc_names.py renamed カイメラ in the uncompressed battle captions
and left 38 in STAGE, because the raw bytes are simply not there to find.

    rename_term.py <iso> --jp カイメラ --to Chimera --from Kaimera [--write]
    rename_term.py <iso> --jp レーベン --to Lowen --from Reben,Raven,Loewen

Usage: rename_term.py <iso> --jp <japanese> --to <english> --from a,b,c [--write]
"""
import hashlib
import io
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


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    # Either one rule via --jp/--to/--from, or many at once via --rules <json>
    # holding [{"jp":..., "to":..., "from":[...]}, ...].
    #
    # ONE PASS matters. Renaming the nine Aquarion names as nine separate runs
    # recompressed the same records nine times, and a record whose fast-packed
    # blob overruns its slot falls back to compress_record_optimal at ~85s. The
    # records overlap heavily, so a single pass is several times less work for
    # byte-identical output.
    rules_path = arg("--rules")
    if rules_path:
        import json
        spec = json.load(io.open(rules_path, encoding="utf-8"))
        RULES = [(r["jp"], r["to"],
                  sorted([v for v in r["from"] if v], key=len, reverse=True))
                 for r in spec]
    else:
        jp_term = arg("--jp")
        good = arg("--to")
        variants = [v for v in (arg("--from") or "").split(",") if v]
        if not (jp_term and good and variants):
            raise SystemExit(__doc__)
        # longest first, so a short variant cannot half-match a longer one
        variants.sort(key=len, reverse=True)
        RULES = [(jp_term, good, variants)]
    RULES = [(t, g, v, t.encode("cp932")) for t, g, v in RULES]

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(open("extracted/DATA_STAGE.BIN", "rb").read())

    edited, inplace, reloc, bad, tally = {}, 0, 0, [], {}
    for idx in range(len(items)):
        e, j = items[idx][1], jp[idx][1]
        if e is None or j is None:
            continue
        eb = bytearray(e)
        jb = bytes(j)
        live = [r for r in RULES if r[3] in jb]
        if not live:
            continue
        ptr = {}
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in ptr:
                ptr[ve] = vj
        touched = False
        for off in sorted(ptr, reverse=True):
            jo = ptr[off]
            zj = jb.find(b"\x00", jo)
            if zj <= jo:
                continue
            # only the rules whose japanese term is in THIS row may touch it
            here = [r for r in live if r[3] in jb[jo:zj]]
            if not here:
                continue
            z = bytes(eb).find(b"\x00", off)
            if z <= off:
                continue
            try:
                s = bytes(eb[off:z]).decode("cp932")
            except Exception:
                continue
            new = s
            for _t, good_i, variants_i, _b in here:
                for v in variants_i:
                    n = len(re.findall(r"\b%s\b" % re.escape(v), new))
                    if n:
                        new = re.sub(r"\b%s\b" % re.escape(v), good_i, new)
                        tally[v] = tally.get(v, 0) + n
            if new == s:
                continue
            nb_lines, ob_lines = new.split("\n")[1:], s.split("\n")[1:]
            worse = (len(nb_lines) > len(ob_lines) or
                     max([cols(b) for b in nb_lines] or [0]) >
                     max([cols(b) for b in ob_lines] or [0]))
            if worse and (len(nb_lines) > MAXLINES or
                          any(cols(b) > WIDTH for b in nb_lines)):
                bad.append((idx, off, "would not fit: %r" % new[:36]))
                for _t, _g, variants_i, _b in here:
                    for v in variants_i:
                        n = len(re.findall(r"\b%s\b" % re.escape(v), s))
                        if n:
                            tally[v] = tally.get(v, 0) - n
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
                    bad.append((idx, off, "no pointer to repoint"))
                    continue
                for y in range(off, k):
                    eb[y] = 0
                reloc += 1
            touched = True
        if touched:
            edited[idx] = bytes(eb)

    for t, g, vs, _b in RULES:
        hits = sum(tally.get(v, 0) for v in vs)
        print("   %-6s %-10s -> %-10s %4d" % (t, ",".join(vs), g, hits))
    print("rows: %d in place, %d relocated | rejected %d" % (inplace, reloc, len(bad)))
    for b in bad[:6]:
        print("   REJECT rec%-4d %#08x %s" % b)
    print("records to rebuild: %d" % len(edited))
    if not write or not edited:
        if not write:
            print("\n(dry run - pass --write to apply)")
        return

    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "analysis", "_lzcache")
    if not os.path.isdir(cdir):
        os.makedirs(cdir)
    for idx, plain in edited.items():
        hdr = items[idx][0]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        key = os.path.join(cdir, "%s.lz" % hashlib.sha1(plain).hexdigest())
        if os.path.exists(key):
            blob = open(key, "rb").read()
        else:
            blob = banlz.compress_record(plain)
            if len(blob) > nxt - hdr:
                blob = banlz.compress_record_optimal(plain)
            open(key, "wb").write(blob)
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
