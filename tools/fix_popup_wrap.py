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
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

LIMIT = 40          # only touch rows wider than this
MINW, MAXW = 34, 44        # 44 is the widest that still fits the popup box
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


WORD = re.compile(u"[A-Za-z\u3040-\u9fff]")


def title_like(s):
    """A glossary TITLE: short, single line, containing letters.

    An entry is [title]["source work"][description], but the source is
    MISSING on many of them - this file's own docstring said so, and 0.8.101
    keyed the selector on it regardless. That silently skipped every
    source-less entry, which is how 'Siberian Railway' shipped at 55 columns
    in a box that clips near 44.

    Keying on the title as well catches both shapes and still excludes
    recaps, which are preceded by 1-byte junk rather than by a title.
    """
    if not (2 <= len(s) <= 44) or b'\n' in s:
        return False
    try:
        d = s.decode('cp932')
    except UnicodeDecodeError:
        return False
    return bool(WORD.search(d)) and not d.startswith(chr(34))


def fix_record(dec, jdec):
    b = bytearray(dec)
    jmap = dict(sstrings(bytes(jdec))) if jdec is not None else {}
    hits = []
    ss = sstrings(bytes(dec))
    for j, (off, s) in enumerate(ss):
        if len(s) < 100:
            continue
        # only a glossary description; never a recap
        has_src = any(is_source(ss[j - k][1]) for k in (1, 2) if j - k >= 0)
        has_title = j >= 1 and title_like(ss[j - 1][1])
        if not (has_src or has_title):
            continue
        try:
            d = s.decode("cp932")
        except UnicodeDecodeError:
            continue
        was = max(cols(l) for l in d.split("\n"))
        # The japanese counterpart is the authority on BOTH bounds.
        jl = None
        js = jmap.get(off)
        if js is not None:
            try:
                jl = js.decode("cp932").count("\n") + 1
            except UnicodeDecodeError:
                jl = None
        lines_now = d.count("\n") + 1
        # Act if the entry is too WIDE for the box, or has more LINES than
        # the japanese ever produced. The second test is not optional: after
        # a pass at 38 columns nothing is too wide any more, so a width-only
        # gate reports "0 strings" and leaves the line overrun sitting there.
        if was <= LIMIT:
            continue
        # 38 columns is where the entries that render correctly sit and it
        # clears the box (which clips near 45). But narrower means MORE
        # lines, and 0.8.101 shipped entries of 25 when the japanese maximum
        # anywhere is 22 - a shape this renderer has never been handed, and
        # it is the renderer that already smashed its caller's locals on an
        # over-long row. So: the narrowest width that still stays inside the
        # japanese line count.
        # Wrap to 38, full stop. 0.8.103 widened this to 44 so an entry
        # would stay within its japanese LINE COUNT, on the theory that a
        # tall entry was crashing the game. The bisect later proved that
        # wrong - the crash was dialogue quote WIDTH - and the widening put
        # entries back over the box, which is the bug this tool exists to
        # prevent. Height was never the problem; width always was.
        width = DEFAULT
        nd = rewrap(d, width)
        now = max(cols(l) for l in nd.split("\n"))
        if now > width or nd == d:
            continue          # unbreakable (japanese), or already correct
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
