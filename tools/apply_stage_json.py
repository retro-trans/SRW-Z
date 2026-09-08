# -*- coding: utf-8 -*-
u"""Apply new dialogue text to STAGE records, keyed, wrapped and byte-fitted.

Input is one or more JSON files mapping key -> the complete new field
("Speaker\\n「body」"). Keys are rec:sha1(japanese):occurrence, the same
identity export_proofread.py emits, and rows are located by pairing english to
japanese THROUGH THE POINTER TABLE - never by offset, which has been wrong
since 0.9.38 relocated our strings.

Each field is re-wrapped to its own box (over-map or scene) with the real glyph
advances, then checked against the slot it must live in. Anything that does not
fit, or needs more than 3 lines, is REPORTED and skipped rather than truncated.

Usage: apply_stage_json.py <rec|all> <out1.json> [<out2.json> ...] [--write]
       "all" takes the records from the keys, so one file can span stages.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import reflow_dialogue as R
import export_proofread as EP

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = "\n"
KAGI = "「"
ISO = "iso/srwz_cap.bin"
JPISO = "iso/srwz.bin"


def wrap_field(field, over, adv):
    sp, _, body = field.partition(NL)
    body = body.strip()
    if body[:1] == "「" and body[-1:] == "」":
        lb, rb, inner = "「", "」", body[1:-1]
    elif body[:1] == "(" and body[-1:] == ")":
        lb, rb, inner = "(", ")", body[1:-1]
    else:
        lb, rb, inner = "", "", body
    inner = inner.replace(NL, " ").strip()
    wl = R.reflow(inner, (R.OVERMAP_PX if over else R.SCENE_PX) - 21, adv)
    if not wl:
        wl = [""]
    wl[0] = lb + wl[0]
    wl[-1] = wl[-1] + rb
    return (sp + NL + NL.join(wl)) if sp else NL.join(wl), len(wl)


def keys_of(eb, jb, rec):
    """offset -> key, exactly as export_proofread numbers them."""
    m = EP.pair(eb, jb)
    occ, out = {}, {}
    for off in sorted(m):
        et, _ = EP.text_at(eb, off)
        if not et or NL not in et:
            continue
        jt, _ = EP.text_at(jb, m[off][0])
        if not jt or KAGI not in jt:
            continue
        h = hashlib.sha1(jt.encode("cp932", "ignore")).hexdigest()[:12]
        n = occ.get(h, 0)
        occ[h] = n + 1
        out[off] = "%d:%s:%d" % (rec, h, n)
    return out


def main():
    rec_arg = sys.argv[1]
    write = "--write" in sys.argv
    files = [a for a in sys.argv[2:] if not a.startswith("--")]

    trans = {}
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        dup = set(trans) & set(d)
        if dup:
            print("  NOTE %d key(s) given twice, later file wins" % len(dup))
        trans.update(d)
    print("translations loaded: %d" % len(trans))

    adv = R.load_adv(ISO)
    f = open(ISO, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    en = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
          if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in en)
    fj = open(JPISO, "rb")
    fj.seek(LBA * SEC)
    jpraw = fj.read(SIZE)
    fj.close()
    jp = [d for h, d in banlz.decompress_all(jpraw)
          if isinstance(h, int) and d is not None]

    if rec_arg == "all":
        recs = sorted({int(k.split(":")[0]) for k in trans})
    else:
        recs = [int(rec_arg)]

    applied = same = 0
    nofit = []
    seen = set()
    touched = {}
    for rec in recs:
        eb = bytes(en[rec][1])
        jb = bytes(jp[rec])
        key_of = keys_of(eb, jb, rec)
        d = en[rec][1]
        bm = R.boxmap(d)
        changed = False
        for off, key in sorted(key_of.items()):
            if key not in trans:
                continue
            seen.add(key)
            z = d.find(b"\x00", off)
            e = z
            while e < len(d) and d[e] == 0:
                e += 1
            slot = e - off - 1
            nf, nl = wrap_field(trans[key], bm.get(off, 1) == 1, adv)
            nb = nf.encode("cp932", "strict")
            if nb == bytes(d[off:z]):
                same += 1
                continue
            if len(nb) > slot or nl > 3:
                nofit.append((key, len(nb), slot, nl, nf.replace(NL, " / ")[:55]))
                continue
            d[off:off + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
            applied += 1
            changed = True
        if changed:
            touched[rec] = bytes(d)

    missing = set(trans) - seen
    print("applied %d, identical %d, did-not-fit %d, key not found %d"
          % (applied, same, len(nofit), len(missing)))
    for x in nofit:
        print("   NOFIT %s  %d B > slot %d, %d line(s)  %r" % x)
    for k in sorted(missing)[:10]:
        print("   NOT FOUND %s" % k)
    print("records touched: %s" % sorted(touched))
    if not touched or not write:
        if touched:
            print("(dry run - pass --write to apply)")
        return 0

    for rec in sorted(touched):
        h = en[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(touched[rec])
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(touched[rec])
        assert len(blob) <= nxt - h, "rec%d over slot (%d > %d)" % (
            rec, len(blob), nxt - h)
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [hh for hh, x in banlz.decompress_all(bytes(raw))
             if isinstance(hh, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == '__main__':          # importable: other tools reuse keys_of/wrap_field
    raise SystemExit(main())
