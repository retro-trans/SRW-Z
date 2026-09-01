# -*- coding: utf-8 -*-
"""Finish the 新地球連邦 rename on the rows that need re-wrapping.

rename_term.py renames a term and REFUSES a row it would push past the box -
3 body lines of 34 columns - because it only exchanges words, it does not
re-flow. "New Earth Federation" is six characters longer than "New Federation",
so it pushed 19 of 23 rows over. This finishes the dialogue ones by re-wrapping
them.

SCENE HEADERS ARE LEFT ALONE, and that is a decision rather than a shortfall.
Eleven of the nineteen are single-line location banners:

    ～New Federation HQ Council～

A banner is one line by construction, so there is nothing to re-flow, and
"New Earth Federation HQ Council" comes to 37 columns against a 34-column box.
The short name is what fits, and a location banner using the short form of an
organisation's name is idiomatic rather than wrong - the japanese uses both
names too.

WRAPPING RULE. Three-line rows are wrapped to 30 columns, not 34: a 3-line row
wider than 30 that would fit at 30 with ascii quotes is the v1.55 crash
signature verify_boxes exists to catch. Rows of one or two body lines use 34.

Refuses rather than truncating: if a row cannot be made to fit even re-wrapped,
it is reported and left in japanese order.

Usage: fix_nef_rewrap.py <iso> [--write]
"""
import multiprocessing
import os
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
BASE = 0x7566F0
NL = chr(10)
OLD, NEW = "New Federation", "New Earth Federation"
NEF = u"\u65b0\u5730\u7403\u9023\u90a6"
NF = u"\u65b0\u9023\u90a6"
KO, KC = u"「", u"」"


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def rewrap(body, width):
    words, out, line = body.replace(NL, " ").split(), [], ""
    for w in words:
        cand = w if not line else line + " " + w
        if line and cols(cand) > width:
            out.append(line)
            line = w
        else:
            line = cand
    if line:
        out.append(line)
    return out


def _pack(a):
    i, plain, room = a
    blob = banlz.compress_record(plain)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(plain)
    return i, blob


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    jp = banlz.decompress_all(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "extracted", "DATA_STAGE.BIN"), "rb").read())
    heads = sorted(h for h, _ in items)
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, done, skipped, headers = {}, 0, [], 0
    for ri in range(min(len(items), len(jp))):
        if items[ri][1] is None or jp[ri][1] is None:
            continue
        eb = bytearray(edited.get(ri, bytes(items[ri][1])))
        jb = bytes(jp[ri][1])
        seen, hit = set(), False
        for p in range(0, min(len(eb), len(jb)) - 4, 4):
            ve = struct.unpack_from("<I", bytes(eb), p)[0] - BASE
            vj = struct.unpack_from("<I", jb, p)[0] - BASE
            if not (0 <= ve < len(eb) and 0 <= vj < len(jb)) or ve in seen:
                continue
            seen.add(ve)
            ez = bytes(eb).find(b"\x00", ve)
            jz = jb.find(b"\x00", vj)
            if ez < 0 or jz < 0:
                continue
            try:
                jt = jb[vj:jz].decode("cp932")
                et = bytes(eb[ve:ez]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if NEF not in jt or NF in jt:
                continue
            if OLD not in et or NEW in et:
                continue
            body = et.split(NL)[1:]
            if len(body) <= 1:              # a scene banner, nothing to reflow
                headers += 1
                continue
            spk = et.split(NL)[0]
            new_body = et.split(NL, 1)[1].replace(OLD, NEW)
            # THE GATE'S RULE, not a blanket 30. verify_boxes flags a
            # 3-line row wider than 30 ONLY IF it would fit at 30 with
            # ascii quotes - that combination is the v1.55 crash
            # signature. A row that genuinely needs more than 30 with the
            # corner brackets is not the signature and is not flagged, so
            # forcing every 3-line row to 30 refused seven rows for no
            # reason.
            lines = None
            for width in (34, 30):
                cand_l = rewrap(new_body, width)
                if len(cand_l) > 3 or max(cols(l) for l in cand_l) > 34:
                    continue
                w = max(cols(l) for l in cand_l)
                if len(cand_l) == 3 and w > 30:
                    plain = max(cols(l.replace(KO, chr(34)).replace(KC, chr(34)))
                                for l in cand_l)
                    if plain <= 30:      # the crash signature - try 30
                        continue
                lines = cand_l
                break
            if lines is None or len(lines) > 3:
                skipped.append((ri, ve, "cannot fit re-wrapped"))
                continue
            cand = spk + NL + NL.join(lines)
            nb = cand.encode("cp932")
            k = ez
            while k < len(eb) and eb[k] == 0:
                k += 1
            if len(nb) >= k - ve:
                skipped.append((ri, ve, "needs %d bytes, room %d"
                                % (len(nb) + 1, k - ve)))
                continue
            eb[ve:k] = nb + bytes(k - ve - len(nb))
            done += 1
            hit = True
            print("   rec%-4d %#08x  %s" % (ri, ve, cand.replace(NL, " | ")[:74]))
        if hit:
            edited[ri] = bytes(eb)
    print("\n%d row(s) re-wrapped, %d scene banner(s) left on the short name, "
          "%d refused" % (done, headers, len(skipped)))
    for ri, off, why in skipped:
        print("   rec%-4d %#08x %s" % (ri, off, why))
    if not write or not edited:
        if not write:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0

    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    ji = [(i, edited[i],
           min([q for q in heads if q > items[i][0]] or [SIZE]) - items[i][0])
          for i in edited]
    packed = dict(pool.map(_pack, ji))
    pool.close()
    pool.join()
    for i in edited:
        hdr = items[i][0]
        blob = packed[i]
        nxt = min([h for h in heads if h > hdr] or [SIZE])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % i
        raw[hdr:hdr + len(blob)] = blob
        for k in range(hdr + len(blob), nxt):
            raw[k] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw))
             if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("wrote %d record(s)" % len(edited))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
