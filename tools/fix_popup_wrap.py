# -*- coding: utf-8 -*-
"""Restore the line breaks that translation dropped from long STAGE strings.

WHAT BROKE
    Opening a 《term》 link in dialogue does NOT read the keyword bank: every
    scene carries its own copy of the entry inside its STAGE record, as
    consecutive strings [title]["source"][description] (the source string is
    missing on some entries). The library reads the bank, the link reads this,
    which is why an entry could open fine from the menu and crash from a link.

    122 long strings render far past their box because the Japanese wrapped
    them with explicit newlines and our English lost them - several are a
    SINGLE line of 400-630 bytes (UN 398, Liff 426, FAITH 473, Trapar 531,
    Exodus 632). 117 of the 122 have a Japanese counterpart at the same offset
    that IS wrapped, which is how we know the breaks belong there.

    The renderer copies a row into a ~520-byte stack buffer. With
    patch_backlog's CONVCOPY hook installed that copy also converts ASCII to
    2-byte private codes, so a 400-byte row wrote ~800 bytes, smashed the
    caller's locals and faulted: TLB Miss pc=0x78bb08 addr=0x78fc1585. With the
    hook reverted the same rows still broke the renderer (VIF FIFO assertion on
    Trapar), so the unbroken line is the defect and the hook only amplified it.

WHAT IT SELECTS
    ONLY glossary descriptions, identified by the quoted source work that
    precedes them ([title]["Combat Mecha Xabungle"][description]). Width alone
    is not enough: scenario recaps are long strings too and they belong in a
    wider box at 56 columns. Selecting on width caught 146 recaps beside the
    64 real entries, and narrowing those would have wrecked every mission
    summary in the game.

HOW IT WRAPS
    To 38 columns. The Japanese box is 24 fullwidth glyphs; against our
    narrower English advance that is about 38 columns, and it is where the
    entries that render correctly already sit.

    The wrap is BYTE-NEUTRAL: only ' ' and '\n' are exchanged, so no string
    changes length, nothing moves, and no pointer needs repointing. Japanese
    text has no spaces to break on and is already at the game's own 48-column
    width, so it is left alone.

Usage: fix_popup_wrap.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

LIMIT = 40          # only touch rows wider than this
MINW, MAXW = 34, 48
DEFAULT = 38                # the 48-column JP box, at 13px per English glyph
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JP_STAGE = os.path.join(WORK, "extracted", "DATA_STAGE.BIN")


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def rewrap(text, width):
    toks = text.replace("\n", " ").split(" ")
    lines, cur = [], []
    for t in toks:
        if cur and cols(" ".join(cur + [t])) > width:
            lines.append(cur)
            cur = [t]
        else:
            cur = cur + [t]
    if cur:
        lines.append(cur)
    return "\n".join(" ".join(l) for l in lines)


def sstrings(b):
    p, out = 0, []
    while p < len(b):
        while p < len(b) and b[p] == 0:
            p += 1
        e = p
        while e < len(b) and b[e] != 0:
            e += 1
        if e > p:
            out.append((p, b[p:e]))
        p = e + 1
    return out


def is_source(s):
    """A glossary entry is stored as [title]["source work"][description].

    That quoted source is the only reliable mark of a glossary description,
    and telling them apart MATTERS: scenario recaps are also long strings and
    they legitimately sit at 56 columns, in a wider box. Selecting on width
    alone caught 146 recaps along with the 64 entries, and re-wrapping those
    to 38 would have narrowed every mission summary in the game.
    """
    try:
        d = s.decode("cp932").strip()
    except UnicodeDecodeError:
        return False
    return len(d) > 2 and d[0] == '"' and d[-1] == '"'


def fix_record(dec, jdec):
    b = bytearray(dec)
    jmap = dict(sstrings(bytes(jdec))) if jdec is not None else {}
    hits = []
    ss = sstrings(bytes(dec))
    for j, (off, s) in enumerate(ss):
        if len(s) < 100:
            continue
        # only a glossary description; never a recap
        if not any(is_source(ss[j - k][1]) for k in (1, 2) if j - k >= 0):
            continue
        try:
            d = s.decode("cp932")
        except UnicodeDecodeError:
            continue
        was = max(cols(l) for l in d.split("\n"))
        if was <= LIMIT:
            continue
        # The Japanese box is 48 COLUMNS (24 fullwidth chars), but our English
        # glyphs advance 13px against fullwidth 21px, so 48 columns of ASCII
        # would be far wider than the same box. Every correctly translated
        # entry in the data sits at 37-38 = 504px / 13, so that - not the
        # Japanese column count - is the English target.
        width = DEFAULT
        nd = rewrap(d, width)
        now = max(cols(l) for l in nd.split("\n"))
        if now > width:
            continue          # no spaces to break on (Japanese) - leave alone
        nb = nd.encode("cp932")
        assert len(nb) == len(s), "not byte-neutral"
        b[off:off + len(nb)] = nb
        hits.append((off, len(s), was, now, width))
    return (bytes(b), hits) if hits else (None, [])


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jp = banlz.decompress_all(bytearray(open(JP_STAGE, "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, total = {}, 0
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        jdec = jp[idx][1] if idx < len(jp) else None
        new, hits = fix_record(bytes(dec), jdec)
        if new is not None:
            edited[idx] = (hdr, new)
            total += len(hits)
            print("rec %-4d %d strings (widest %d -> %d)"
                  % (idx, len(hits), max(h[2] for h in hits),
                     max(h[3] for h in hits)))
    print("\n%d strings re-wrapped in %d records" % (total, len(edited)))
    if dry or not edited:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    packed = dict(pool.map(_compress, [(i, d) for i, (h, d) in edited.items()]))
    pool.close(); pool.join()

    for idx, (hdr, plain) in edited.items():
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(h for h, _ in edited.values()), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
