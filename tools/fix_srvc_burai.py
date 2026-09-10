# -*- coding: utf-8 -*-
u"""\u30d6\u30e9\u30a4\u5927\u5e1d is Emperor Burai, and 20 battle captions still say "Brai".

name_sweep.py has carried \u30d6\u30e9\u30a4 -> Burai since 0.9.x, but name_sweep works
from analysis/proofread/dialogue.json - STAGE dialogue only. The SRVC caption
pool is outside it, exactly as the rec0 stage summaries were, so the rule has
never once reached these lines. Canon is getterrobo.fandom.com (Emperor Burai),
already recorded in fix_terms_grow.py.

WHOLE CAPTIONS ARE REPLACED, NOT THE WORD. "Brai" -> "Burai" grows by a byte,
and a caption may not change length: the pool is NUL-separated and scripted
attack sequences fetch their lines BY BYTE OFFSET from tables this does not
rebuild, so one long string slides every offset after it in its block
([[srvc-byte-budget]] is about srvc_apply --free; a raw byte edit has no such
luxury). Each replacement below is therefore the EXACT byte length of the line
it replaces, verified by assert before anything is written.

Paying that byte costs the title "Emperor" in two of the six, which is the
honest trade - the alternative was dropping the closing "!" on all of them and
making shouted battle lines read like truncations.

SRVC exists twice in the image (the original extent and the relocated copy
srvc_apply --free made), so every occurrence in the whole file is fixed.

Usage: fix_srvc_burai.py <iso> [--write]
"""
import sys

# (old caption, new caption) - both include the ASCII quotes the pool uses
PAIRS = [
    (u'"E-Emperor Brai! Forgive me!"', u'"E-Emperor Burai! Pardon me!"'),
    (u'"Em-Emperor Brai!!"',           u'"E-Emperor Burai!!"'),
    (u'"Emperor Brai, prepare!"',      u'"Emperor Burai, perish!"'),
    (u'"End, Emperor Brai!"',          u'"Burai, this is it!"'),
    (u'"Prepare, Emperor Brai!"',      u'"Ready yourself, Burai!"'),
    (u'"This life\'s already Brai\'s!"', u'"My life is Emperor Burai\'s!"'),
]


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    pairs = []
    for a, b in PAIRS:
        ab, bb = a.encode("cp932"), b.encode("cp932")
        assert len(ab) == len(bb), "%r %d != %r %d" % (a, len(ab), b, len(bb))
        pairs.append((ab, bb))
    f = open(iso, "r+b" if write else "rb")
    CH = 1 << 24
    off, prev, hits = 0, b"", []
    while True:
        blk = f.read(CH)
        if not blk:
            break
        buf = prev + blk
        base = off - len(prev)
        for ab, bb in pairs:
            i = buf.find(ab)
            while i >= 0:
                # the match must BE a whole pool entry: NUL on both sides
                if (i == 0 or buf[i - 1] == 0) and \
                        i + len(ab) < len(buf) and buf[i + len(ab)] == 0:
                    hits.append((base + i, ab, bb))
                i = buf.find(ab, i + 1)
        prev = buf[-512:]
        off += len(blk)
    seen, uniq = set(), []
    for pos, ab, bb in hits:
        if pos in seen:
            continue
        seen.add(pos)
        uniq.append((pos, ab, bb))
    print("captions to fix: %d" % len(uniq))
    for pos, ab, bb in sorted(uniq):
        print("   %#012x %-30s -> %s" % (pos, ab.decode("cp932"), bb.decode("cp932")))
    if not write or not uniq:
        if not write:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return 0
    for pos, ab, bb in uniq:
        f.seek(pos)
        assert f.read(len(ab)) == ab, "moved under us at %#x" % pos
        f.seek(pos)
        f.write(bb)
    f.close()
    g = open(iso, "rb")
    bad = 0
    for pos, ab, bb in uniq:
        g.seek(pos)
        if g.read(len(bb)) != bb:
            bad += 1
    g.close()
    print("written and re-read: %d ok, %d bad" % (len(uniq) - bad, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
