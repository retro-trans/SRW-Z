# -*- coding: utf-8 -*-
u"""The rec0 stage-summary prose - a pool no dialogue pass has ever read.

rec0 holds the "story so far" recap shown before each stage: 110 fields of
plain prose. They carry no \u300c\u300d, so
[[dialogue-identified-by-japanese-bracket]] applies - dialogue.json never
exported them, the sheets never held them, and name_sweep, which works from
that json, has never reached a single one. Every spelling this project has
settled is therefore still stale here.

Two classes are fixed:

STRAY TAILS. Seven summaries have garbage welded onto the last sentence -
"with Baldios\uff0es\uff0e", "of Chiram\uff0eD", "to help the group\uff0ep\uff0e". A stray letter
after the closing period is the signature; it is not in the japanese, and it
is in the string rather than past its terminator.

NAMES. name_sweep.SUBS is imported rather than copied, so this pool gets the
same decisions as the dialogue and cannot drift from them again. One extra
outlier is handled here: a single summary punctuates with ASCII "." while the
other 109 use the full-width \uff0e, and 0x2E is a control byte to the menu blit
([[halfwidth-digits]]).

WRAPPING. A substitution that grows ("King Vega" -> "Emperor Vega") can push
a line past the widest the box is known to hold, so a field is re-wrapped -
to 56 columns, which the japanese itself uses in 108 of these 110 fields -
only when a line would otherwise exceed it. Growing the width is safe;
NARROWING one would make the entry taller ([[wrap-bounds-both-ways]]), and
the japanese proves 11 lines against our longest 12, so a re-wrap to 56 can
only ever shorten these.

Every field is rewritten inside its own NUL-padded slot: no offset moves.

Usage: fix_stage_summaries.py <iso> <jp-iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import name_sweep as NS

SEC, LBA, SIZE = 2048, 1651029, 3910128
FW = u'\uff0e'
WIDTH = 56

# offset in rec0 -> ordered (old, new) pairs applied before the name sweep
EDITS = {
    0x71d0: [(u'Baldios' + FW + u's' + FW, u'Baldios' + FW)],
    0x9ce0: [(u'Chiram' + FW + u'D', u'Chiram' + FW)],
    0xaa20: [(u'Black Charisma' + FW + u'"', u'Black Charisma"' + FW)],
    0xc040: [(u'group' + FW + u'p' + FW, u'group' + FW)],
    0xd530: [(u'expression' + FW + u'D', u'expression' + FW)],
    0xded0: [(u'Dorothy' + FW + u'D', u'Dorothy' + FW)],
    0xefe0: [(u'Gainer' + FW + u'D', u'Gainer' + FW)],
    # the ASCII-punctuated outlier, plus its leading space
    0x8ef0: [(u'. ', FW + u' '), (u'ached.', u'ached' + FW)],
    # Two fields have no padding at all, so a growing name has to be paid for
    # in the same sentence. Both are byte-neutral rewordings, applied BEFORE
    # the sweep so its own rule finds nothing left to change.
    0x6ab0: [(u'mysterious space craft', u'mysterious spacecraft')],
    0xe8b0: [(u'a King Vega determined to die fighting',
              u'Emperor Vega, bent on dying in battle')],
}


def cols(s):
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def rewrap(body, width=WIDTH):
    out, cur = [], u''
    for t in u' '.join(body.split()).split(u' '):
        cand = t if not cur else cur + u' ' + t
        if cols(cand) <= width:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = t
    if cur:
        out.append(cur)
    return u'\n'.join(out)


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

    h0, d = live[0]
    jb = bytes(jp[0])
    subs = [(re.compile(p), r) for p, r in NS.SUBS]
    ok, changed, hits, wrapped = True, 0, {}, 0
    for ve, (vj, p) in sorted(EP.pair(bytes(d), jb).items()):
        e, room = EP.text_at(bytes(d), ve)
        j, _ = EP.text_at(jb, vj)
        if not e or not j or len(e) < 120:
            continue                       # prose only; the short fields are
        # FLATTEN FIRST. Every one of these fields is a single wrapped
        # paragraph, and a term that straddles a line break is invisible to a
        # literal-space pattern - the trap that has now silently defeated four
        # separate sweeps ([[term-split-by-linebreak]]). "Dark History" wraps
        # in this pool exactly that way.
        assert all(l.strip() for l in e.split(u'\n')), "%#x: blank line" % ve
        width = max(cols(l) for l in e.split(u'\n'))
        new = u' '.join(e.split())
        for old, rep in EDITS.get(ve, []):
            if old not in new:
                print("  %#x: MISSING %r" % (ve, old))
                ok = False
                continue
            new = new.replace(old, rep)
        for rx, rep in subs:
            n2 = rx.sub(rep, new)
            if n2 != new:
                hits[rep] = hits.get(rep, 0) + len(rx.findall(new))
                new = n2
        assert u'.' not in new or ve != 0x8ef0, "%#x: ASCII period left" % ve
        if new == u' '.join(e.split()):
            continue
        # Re-wrapped to the field's OWN widest line, never wider and never
        # narrower: a greedy wrap at that width can never need more lines than
        # the wrap already on the disc, and narrowing is what makes an entry
        # taller ([[wrap-bounds-both-ways]]). If it still will not fit, fall
        # back to the 56 columns the japanese uses in 108 of these 110 fields.
        new = rewrap(new, width)
        wrapped += 1
        if len(new.encode('cp932')) > room - 1 and width < WIDTH:
            new = rewrap(new, WIDTH)
        nb = new.encode('cp932')
        if len(nb) > room - 1:
            print("  %#x: %d B > budget %d, SKIPPED" % (ve, len(nb), room - 1))
            ok = False
            continue
        z = bytes(d).find(b"\x00", ve)
        d[ve:z] = b"\x00" * (z - ve)
        d[ve:ve + len(nb)] = nb
        changed += 1
    for k, v in sorted(hits.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (k, v))
    print("summaries rewritten: %d (%d re-wrapped)" % (changed, wrapped))
    if not ok:
        print("refusing to write")
        f.close()
        return 1
    if not changed or not write:
        if changed:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0
    nxt = min([x for x in heads if x > h0] or [len(raw)])
    blob = banlz.compress_record(bytes(d))
    if len(blob) > nxt - h0:
        blob = banlz.compress_record_optimal(bytes(d))
    assert len(blob) <= nxt - h0, "rec0 over slot"
    raw[h0:h0 + len(blob)] = blob
    for x in range(h0 + len(blob), nxt):
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
