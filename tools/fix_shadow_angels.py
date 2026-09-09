# -*- coding: utf-8 -*-
u"""Settle 堕天翅 on one english name, and fix the strings that lost it.

堕天翅 is Genesis of Aquarion's antagonists. analysis/glossary.json has
settled the name as "Shadow Angels" and 403 of the 454 strings whose
japanese carries the term already use it. The rest do not, and this
closes the gap.

Counted on the disc, flattened (a term split across a line break is
invisible to a raw match - see [[term-split-by-linebreak]], which is why
an earlier count of mine read 75 bare "Angels" that were really
"Shadow\\nAngels"):

    Shadow Angel(s)   403      the settled name
    bare "Angels"      20      anaphora after a full mention - left alone
    no term            14      "they"/"them" - left alone
    Fallen Wings       12      a second name used through one record
    invented name       4      "Dushantens", "Dekarar", "fallen insects"
    UNTRANSLATED        1      the english field is the japanese, verbatim

The eleven "Fallen Wings" rows whose japanese uses 「」 go through
apply_lines_relocating, which re-wraps them. This tool takes the six that
cannot: one parenthesised thought (its japanese uses （）, so it has no
export key at all - see [[dialogue-identified-by-japanese-bracket]]),
three long-form recap paragraphs that the relocating applier refuses by
design, and the two briefing conditions, which are not dialogue fields.

Replacements are DERIVED from each row's own text, never retyped. The
recaps are re-wrapped to their own existing width, because "Dushantens"
-> "Shadow Angels" pushes one line from 56 to 59 columns.

Usage: fix_shadow_angels.py <iso> <jp-iso> [--write]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = "\n"

# (record, a substring that identifies the row, old, new)
# old=None means the whole field is replaced - those two are the briefing
# conditions, whose japanese is a bare noun phrase and not a dialogue box.
EDITS = [
    (22, u"A war between humans and the", u"Fallen Wings", u"Shadow Angels",
     "speaker"),
    (0, u"Then the enemy Dushantens appeared", u"Dushantens",
     u"Shadow Angels", "prose"),
    (0, u"joined the chaos", u"Dushantens", u"Shadow Angels", "prose"),
    (0, u"repelled the fallen insects", u"fallen insects", u"Shadow Angels",
     "prose"),
    # 堕天翅のマップ西端到達。 - "Dekarar" is not a name in this game, and the
    # word order was broken too. Its siblings read "Coralians reach the
    # south edge" / "Soleil reaches the map edge．"
    (37, u"reach map west edge", None, u"Shadow Angels reach the west edge．",
     "full"),
    # 堕天翅登場から４ターンが経過する。 shipped as raw japanese. Full-width
    # digits, like every other condition string in this panel.
    (117, u"堕天翅登場", None,
     u"Survive ４ turns after Shadow Angels appear．", "full"),
]


def rewrap(body, width):
    u"""Re-flow one paragraph to `width`, keeping blank lines."""
    out = []
    for para in body.split(NL + NL):
        words = para.split()
        line, lines = "", []
        for w in words:
            if line and len(line) + 1 + len(w) > width:
                lines.append(line)
                line = w
            else:
                line = w if not line else line + " " + w
        if line:
            lines.append(line)
        out.append(NL.join(lines))
    return (NL + NL).join(out)


def field_at(b, i):
    u"""The whole NUL-delimited string containing byte offset i."""
    s = b.rfind(b"\x00", 0, i) + 1
    z = b.find(b"\x00", i)
    return s, z


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    g = open(jpiso, "rb")
    g.seek(LBA * SEC)
    jp = [d for h, d in banlz.decompress_all(g.read(SIZE))
          if isinstance(h, int) and d is not None]
    g.close()

    touched = {}
    done = 0
    for rec, locator, old, new, kind in EDITS:
        d = live[rec][1]
        eb = bytes(d)
        jb = bytes(jp[rec])
        i = eb.find(locator.encode("cp932"))
        if i < 0:
            print("  rec%-4d locator not found: %r" % (rec, locator))
            continue
        off, z = field_at(eb, i)
        cur = eb[off:z].decode("cp932")
        k = z
        while k < len(eb) and eb[k] == 0:
            k += 1
        budget = k - off - 1
        if kind == "full":
            nxt = new
        elif kind == "speaker":
            # FLATTEN BEFORE REPLACING. The term is split across a line
            # break here, so "Fallen\nWings" does not match "Fallen Wings" -
            # which is exactly how this tool missed it on its first run.
            sp, _, body = cur.partition(NL)
            width = max(len(x) for x in body.split(NL))
            nxt = sp + NL + rewrap(" ".join(body.split()).replace(old, new),
                                   width)
        else:
            width = max(len(x) for x in cur.split(NL))
            nxt = rewrap(" ".join(cur.split()).replace(old, new), width)
        if old is not None and old in " ".join(nxt.split()):
            print("  rec%-4d term survived the replace, SKIPPED" % rec)
            continue
        nb = nxt.encode("cp932")
        if len(nb) > budget:
            print("  rec%-4d %d B > budget %d, SKIPPED" % (rec, len(nb), budget))
            continue
        smask = X.safe_mask(jb)
        if not all(d[x] == 0 and smask[x] for x in range(z, off + len(nb))):
            print("  rec%-4d growth would cross structure, SKIPPED" % rec)
            continue
        pm = F.pointer_map(eb)
        if any(off < v < max(z, off + len(nb)) for v in pm):
            print("  rec%-4d a pointer aims inside this field, SKIPPED" % rec)
            continue
        d[off:off + len(nb)] = nb
        for x in range(off + len(nb), max(z, off + len(nb))):
            d[x] = 0
        d[off + len(nb)] = 0
        touched[rec] = True
        done += 1
        print("  rec%-4d @%#07x  %d -> %d lines, %d -> %d B"
              % (rec, off, cur.count(NL) + 1, nxt.count(NL) + 1,
                 len(cur.encode("cp932")), len(nb)))
        print("       was %r" % cur.replace(NL, " | ")[:74])
        print("       now %r" % nxt.replace(NL, " | ")[:74])

    print("")
    print("strings fixed: %d of %d" % (done, len(EDITS)))
    if not touched or not write:
        if touched:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0
    for rec in sorted(touched):
        h = live[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(bytes(live[rec][1]))
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(bytes(live[rec][1]))
        assert len(blob) <= nxt - h, "rec%d over slot" % rec
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
