# -*- coding: utf-8 -*-
"""Pull every battle line ONE character speaks, japanese beside our english.

Captions carry no speaker field - the name in the box comes from whoever plays
the voice clip. But the sequence record's first u16 IS the clip id, and clips
are banked per character: Rand's run 32076-32405 and end exactly where Mel's
begin at 32406. So a character's whole set is a contiguous id range, and that
is what makes a per-character proofread possible at all.

Reading one character end to end is worth more than reading a ranked sample.
It is the only way the term drift shows up - ビーター殺法 had four different
english names, and 姐さん had four, one of which ("boss") was already 親方's.
No line looks wrong on its own; they only disagree with each other.

    character_lines.py --find パワー勝負      which bank holds this line?
    character_lines.py 32076 32405            dump a bank
    character_lines.py 32076 32405 -o rand.tsv

Finding a bank: pass --find with a phrase you know the character says, take the
clip id it reports, then dump a generous range around it and look for where the
voice changes. The edges are obvious in the text.

Checking a bank is really one character: --check reports japanese lines with
feminine sentence-enders inside it, which catches a co-pilot's lines mixed in.
One hit in Rand's 317 was a genuine Mel reaction, not a banding error.

Usage: character_lines.py <lo> <hi> [-o out.tsv] [--check]
       character_lines.py --find <japanese substring>
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import srvc
import srvc_records

IDSP = u"\u3000"
BS = chr(92) + "n"
FEM = (u"のよね", u"のよ！", u"わよ", u"かしら", u"あたし", u"だわ", u"なさいよ")


def load_en():
    work = json.load(io.open(os.path.join(ROOT, "analysis", "srvc_work.json"),
                             encoding="utf-8"))
    en = json.load(io.open(os.path.join(ROOT, "analysis", "srvc_en.json"),
                           encoding="utf-8"))
    idx = {}
    for x in work:
        idx.setdefault(x["jp"], x["i"])

    def lookup(jp):
        # srvc_work strips the quote marks and drops the ideographic spaces
        # that sit against a line break; the disc keeps them. Try both.
        b = jp.strip(u"\u300c\u300d")
        for k in (jp, b, b.replace(IDSP + BS + IDSP, BS),
                  b.replace(BS + IDSP, BS), b.replace(IDSP + BS, BS),
                  b.replace(IDSP, u"")):
            if k in idx:
                return idx[k]
        return None
    return lookup, en


def walk():
    """Yield (clip_id, japanese) for every resolved sequence record."""
    orig = open(os.path.join(ROOT, "extracted", "BTL_SRVC.BIN"), "rb").read()
    oseg = srvc.read_seg(open(os.path.join(ROOT, "extracted",
                                           "BTL_SRVC.SEG"), "rb").read())
    blocks = srvc.parse(orig, oseg)
    recs, _ = srvc_records.resolve(blocks)
    for bi, rs in recs.items():
        pool = blocks[bi].strings
        raw = b"\x00".join(pool) + b"\x00"
        for pos, tgt, _anchor in rs:
            if pos + 2 > len(raw) or tgt >= len(pool):
                continue
            try:
                yield struct.unpack_from("<H", raw, pos)[0], pool[tgt].decode("cp932")
            except Exception:
                continue


def main():
    if not sys.argv[1:]:
        raise SystemExit(__doc__)
    if sys.argv[1] == "--find":
        needle = sys.argv[2].decode("utf-8") if str is bytes else sys.argv[2]
        hits = {}
        for clip, jp in walk():
            if needle in jp:
                hits.setdefault(clip, jp)
        if not hits:
            print("no caption contains %s" % needle)
            return 1
        for clip in sorted(hits):
            print("clip %6d  %s" % (clip, hits[clip].replace(BS, " / ")))
        print("\n%d clip(s). Dump a range around these to find the bank edges."
              % len(hits))
        return 0

    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    lookup, en = load_en()
    seen, rows = set(), []
    for clip, jp in walk():
        if not (lo <= clip <= hi) or jp in seen:
            continue
        seen.add(jp)
        i = lookup(jp)
        rows.append((clip, i, jp, en.get(str(i)) if i is not None else None))
    rows.sort()
    miss = [r for r in rows if r[3] is None]
    print("clips %d-%d: %d distinct lines, %d with no english"
          % (lo, hi, len(rows), len(miss)))
    if "--check" in sys.argv:
        odd = [r for r in rows if any(m in r[2] for m in FEM)]
        print("lines with feminine sentence-enders: %d%s"
              % (len(odd), " (check these are not a co-pilot's)" if odd else ""))
        for r in odd:
            print("   clip %d  %s" % (r[0], r[2]))
        return 0
    if out:
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            for clip, i, jp, e in rows:
                f.write(u"%d\t%s\t%s\t%s\n" % (clip, i, jp, e))
        print("wrote %s" % out)
    else:
        for clip, i, jp, e in rows:
            print("%d i=%s\n  JP %s\n  EN %s" % (clip, i, jp, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
