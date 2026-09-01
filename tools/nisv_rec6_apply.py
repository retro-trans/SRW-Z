# -*- coding: utf-8 -*-
"""Translate the rec6 help book and repack it.

The english is analysis/help_en.json, keyed by sha1 of the japanese paragraph
(see nisv_rec6_dump.py) so that no japanese prose is committed.

Each translated paragraph is re-wrapped to the panel and re-emitted as
absolutely positioned runs, because the renderer does no wrapping of its own.
Untranslated paragraphs are re-emitted unchanged, at their authored line
breaks, so a partial translation is always safe to ship.

Sections are then REPACKED: every section's size lives in the index, so they
can be resized freely and the record's decompressed length held exactly
constant. That matters - rec6 loads into a fixed RAM buffer, and growing a
decompressed record is what killed the uncompressed-STAGE experiment.

Usage: nisv_rec6_apply.py <iso> [--write] [--verbose]
"""
import hashlib
import io
import json
import multiprocessing
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import nisv_rec6
import nisv_rec6_para as para

LBA, SECT = 1568269, 272
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_PATH = ROOT + "/analysis/help_en.json"
ALIGN = 16


def key(text):
    return hashlib.sha1(text.encode("cp932", "ignore")).hexdigest()[:16]


def load_en():
    if not os.path.exists(EN_PATH):
        return {}
    raw = json.load(io.open(EN_PATH, encoding="utf-8"))
    return dict((k, v) for k, v in raw.items() if not k.startswith("_"))


def _prefix(text):
    """The plain text before the first inline span, if the paragraph has one."""
    i = text.find("{a=")
    return text[:i] if i > 0 else None


def retune_indent(p, text):
    """Realign a hanging indent that was aligned to an inline span.

    Rows like 攻撃時：{a=03}...{/a} set cont_x to exactly first_x plus the
    width of the label, so the wrapped text hangs under the span rather than
    under the label. The english label is a different width, so that has to be
    recomputed or the continuation lines no longer line up.
    """
    jp_prefix = _prefix(p.text)
    if jp_prefix is None:
        return p.cont_x
    if p.cont_x != p.first_x + para.px(jp_prefix):
        return p.cont_x                        # not aligned to the span
    en_prefix = _prefix(text)
    if en_prefix is None:
        return p.cont_x
    return p.first_x + para.px(en_prefix)


def translate_section(sec, en, stats):
    """Re-emit one section, translating the paragraphs we have english for."""
    paras = para.group(sec.runs)

    def lines_for(p):
        entry = en.get(key(p.text))
        if entry is None:
            return p.lines                     # leave the japanese alone
        if isinstance(entry, dict):
            text, cx = entry["t"], entry.get("cx")
        else:
            text, cx = entry, None
        p.cont_x = cx if cx is not None else retune_indent(p, text)
        q = para.Para(p.kind, p.attr, p.first_x, p.cont_x, p.y, [text], " ")
        return para.wrap(q)

    stats[0] += sum(1 for p in paras if key(p.text) in en)
    stats[1] += len(paras)
    para.avoid_collisions(paras, lines_for)
    sec.runs = para.place(paras, lines_for)
    return sec


def repack(b, secs, base):
    """Rebuild the record: sections laid out contiguously, index rewritten.

    The total length is held identical to the original.
    """
    out = bytearray(len(b))
    out[0:8] = b[0:8]                           # count, base
    off = base
    for s in secs:
        if s.runs is None:
            body = b[s.off:s.off + s.size]      # section 0 is binary
        else:
            packed = s.body()
            body = struct.pack("<H", len(packed)) + packed
        size = (len(body) + ALIGN - 1) // ALIGN * ALIGN
        if off + size > len(b):
            raise ValueError("rec6 overflows at section %d: needs %d, has %d"
                             % (s.index, off + size, len(b)))
        out[off:off + len(body)] = body
        struct.pack_into("<II", out, 8 + 8 * s.index, off - base, size)
        off += size
    return bytes(out), off


def _pack(a):
    plain, room = a
    blob = banlz.compress_record(plain)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(plain)
    return blob


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    verbose = "--verbose" in sys.argv
    en = load_en()
    print("english entries: %d" % len(en))

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * 2048)
    raw = bytearray(f.read(SECT * 2048))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, _ in items)
    hdr = items[6][0]
    b = bytes(items[6][1])

    secs, base = nisv_rec6.parse(b)
    stats = [0, 0]
    for s in secs:
        if s.runs is not None:
            translate_section(s, en, stats)
    print("paragraphs translated: %d / %d" % (stats[0], stats[1]))

    nb, used = repack(b, secs, base)
    print("repacked: %d of %d bytes used (%d free), size unchanged: %s"
          % (used, len(b), len(b) - used, len(nb) == len(b)))

    # the rebuilt record must still parse, and every section must round-trip
    chk, _ = nisv_rec6.parse(nb)
    assert len(chk) == len(secs), "section count changed"
    for a, c in zip(secs, chk):
        if a.runs is None:
            continue
        assert c.runs is not None, "section %d stopped parsing" % a.index
        # compare the PACKED bytes: the text differs by design after a
        # round-trip, because pack() sends . / 0-9 : ; < = out fullwidth.
        assert [r.pack() for r in a.runs] == [r.pack() for r in c.runs], \
               "section %d did not round-trip" % a.index
    print("re-parse: all %d sections round-trip" % len(chk))

    tall = [(s.index, max(r.y for r in s.runs)) for s in secs
            if s.runs and max(r.y for r in s.runs) > 652]
    if tall:
        print("OVER 652px tall: %s" % tall[:10])
    if verbose:
        for s in secs:
            if s.runs:
                print("  sec%-4d %d runs, %d bytes"
                      % (s.index, len(s.runs), len(s.body()) + 2))

    if not write:
        print("(dry run - pass --write to apply)")
        f.close()
        return 1 if tall else 0

    nxt = min([h for h in heads if h > hdr] or [len(raw)])
    blob = _pack((nb, nxt - hdr))
    if len(blob) > nxt - hdr:
        print("COMPRESSED OVERFLOW: %d > %d" % (len(blob), nxt - hdr))
        f.close()
        return 1
    raw[hdr:hdr + len(blob)] = blob
    for k in range(hdr + len(blob), nxt):
        raw[k] = 0
    check = banlz.decompress_all(bytes(raw))
    assert len(check) == len(items), "record count changed"
    assert bytes(check[6][1]) == nb, "rec6 did not survive the round trip"
    f.seek(LBA * 2048)
    f.write(bytes(raw))
    f.close()
    print("rec6 written: %d compressed bytes (slot %d)" % (len(blob), nxt - hdr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
