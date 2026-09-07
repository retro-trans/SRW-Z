# -*- coding: utf-8 -*-
u"""Apply a fresh translation of one STAGE record, keyed, wrapped and byte-fitted.

Input is one or more JSON files mapping key -> the complete new field
("Speaker\\n「body」"). Keys are rec:sha1(japanese):occurrence, the same
identity export_proofread.py emits, and rows are located by pairing english to
japanese THROUGH THE POINTER TABLE - never by offset, which has been wrong
since 0.9.38 relocated our strings.

Each field is re-wrapped to its own box (over-map or scene) with the real glyph
advances, then checked against the slot it must live in. Anything that does not
fit, or needs more than 3 lines, is REPORTED and skipped rather than truncated.

Usage: apply_stage_json.py <rec> <out1.json> [<out2.json> ...] [--write]
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


def main():
    rec = int(sys.argv[1])
    write = "--write" in sys.argv
    files = [a for a in sys.argv[2:] if not a.startswith("--")]
    trans = {}
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        dup = set(trans) & set(d)
        if dup:
            print("  NOTE %d key(s) given twice, later file wins: %s"
                  % (len(dup), list(dup)[:3]))
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

    eb = bytes(en[rec][1])
    jb = bytes(jp[rec])
    m = EP.pair(eb, jb)
    occ, key_of = {}, {}
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
        key_of[off] = "%d:%s:%d" % (rec, h, n)

    d = en[rec][1]
    bm = R.boxmap(d)
    applied, same, nofit, unknown = 0, 0, [], set(trans)
    for off in sorted(m):
        key = key_of.get(off)
        if not key or key not in trans:
            continue
        unknown.discard(key)
        z = d.find(b"\x00", off)
        e = z
        while e < len(d) and d[e] == 0:
            e += 1
        slot = e - off - 1
        over = bm.get(off, 1) == 1
        nf, nl = wrap_field(trans[key], over, adv)
        nb = nf.encode("cp932", "strict")
        if nb == bytes(d[off:z]):
            same += 1
            continue
        if len(nb) > slot or nl > 3:
            nofit.append((key, len(nb), slot, nl, nf.replace(NL, " / ")[:60]))
            continue
        d[off:off + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
        applied += 1

    print("rec%d: applied %d, identical %d, did-not-fit %d, key not found %d"
          % (rec, applied, same, len(nofit), len(unknown)))
    for x in nofit:
        print("   NOFIT %s  %d B > slot %d, %d line(s)  %r" % x)
    for k in list(unknown)[:10]:
        print("   NOT FOUND %s" % k)
    if not applied or not write:
        if applied:
            print("(dry run - pass --write to apply)")
        return 0

    h = en[rec][0]
    nxt = min([x for x in heads if x > h] or [len(raw)])
    dd = bytes(d)
    blob = banlz.compress_record(dd)
    if len(blob) > nxt - h:
        blob = banlz.compress_record_optimal(dd)
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


raise SystemExit(main())
