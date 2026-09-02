# -*- coding: utf-8 -*-
"""Apply a fresh translation of one STAGE record, row by row, from a json map.

Written for the stage 35 retranslation. The translator (me) writes ONE
unwrapped english sentence per row; this wraps it, checks it against the box
and against the row's real byte slot, and refuses anything that does not fit
rather than truncating it.

Input: {"<key>": "<english body, unwrapped>", ...} where <key> is the stable
`rec:sha1(japanese)[:12]:occurrence` used by export_proofread.py and the
proofreading sheet. Keying on the japanese hash means the map survives
re-ordering, re-wrapping and rebuilds - a byte offset would not.

The speaker line is preserved from the disc, never retranslated here: speaker
names are settled against the wiki elsewhere and must not drift per-row.

Wrapping is the same punctuation-aware DP as debracket_stage.py - each line
charged the square of its width, refunded for ending on a pause - so the new
text breaks the way the rest of the record does.

Usage: apply_retrans.py <iso> <record> <map.json> [--write]
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import hashlib
from debracket_stage import wrap_balanced, cols, widest

SEC = 2048
LBA, SIZE = 1651029, 3910128
WIDTH, MAXLINES = 34, 3
JP_ISO = "iso/srwz.bin"


def fields(blob):
    """(offset, slot, text) for every NUL-terminated run that decodes."""
    d = bytes(blob)
    pos = 0
    while pos < len(d):
        z = d.find(b"\x00", pos)
        if z < 0:
            break
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        if z > pos:
            try:
                yield pos, k - pos - 1, d[pos:z].decode("cp932")
            except UnicodeDecodeError:
                pass
        pos = k


def main():
    iso, rec, mapfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    write = "--write" in sys.argv
    table = json.load(io.open(mapfile, encoding="utf-8"))

    jf = open(JP_ISO, "rb")
    jf.seek(LBA * SEC)
    jlive = [(h, d) for h, d in banlz.decompress_all(jf.read(SIZE))
             if isinstance(h, int) and d is not None]
    jf.close()

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    hdr, data = live[rec]
    d = bytearray(data)

    # japanese by offset: STAGE is spliced in place, so a field sits at the
    # same offset in the virgin disc and in ours
    jp_at = dict((off, t) for off, _s, t in fields(jlive[rec][1]))

    occ = {}
    done = skipped = 0
    for off, slot, text in list(fields(d)):
        jt = jp_at.get(off)
        if not jt or u"\n" not in jt:
            continue
        h = hashlib.sha1(jt.encode("cp932", "ignore")).hexdigest()[:12]
        n = occ.get(h, 0)
        occ[h] = n + 1
        key = "%d:%s:%d" % (rec, h, n)
        body = table.get(key)
        if body is None:
            continue
        speaker = text.split(u"\n")[0]
        lines = wrap_balanced(u" ".join(body.split()), WIDTH)
        new = speaker + u"\n" + u"\n".join(lines)
        nb = new.encode("cp932")
        why = None
        if len(lines) > MAXLINES:
            why = "%d lines" % len(lines)
        elif max(cols(l) for l in lines) > WIDTH:
            why = "%d cols" % max(cols(l) for l in lines)
        elif len(nb) > slot:
            why = "%d bytes over slot %d" % (len(nb), slot)
        if why:
            print("  REFUSED %s  (%s)" % (key, why))
            print("     %s" % body)
            skipped += 1
            continue
        if new == text:
            continue
        d[off:off + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
        done += 1

    print("\n%d row(s) retranslated, %d refused" % (done, skipped))
    missing = [k for k in table if not k.startswith("%d:" % rec)]
    for m in missing:
        print("  key not for rec%d: %s" % (rec, m))
    if write and done and not skipped:
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % rec
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif write and skipped:
        print("NOTHING WRITTEN - fix the refused rows first")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
