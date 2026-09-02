# -*- coding: utf-8 -*-
"""Drop the japanese corner brackets from a stage's dialogue and re-wrap it.

The shipped script wraps every spoken line in 「」. Those brackets do no work
in the engine: a dialogue field is stored as

    speaker \n body-line \n body-line \n body-line

and the renderer already takes line 1 as the name plate. The brackets sit
inside the body text, so nothing parses them - they are purely visual. Nor do
they separate speech from thought, which is the reason I first argued for
keeping them: thought lines are written 「(...)」, brackets AND parens, so the
parens are what carry that distinction.

What they cost is room. 「 and 」 are full-width: 2 bytes and 2 columns each, so
every row gives back 4 of each - out of a box that is only 34 columns by 3
lines. That is the tightest constraint in this translation.

RE-WRAPPING. Stripping alone leaves the old line breaks in place, so lines
just end 4 columns short and the text reads ragged. Every row is therefore
re-flowed greedily into the freed space, which also lets some three-line rows
settle onto two.

Rows containing $n / $c / $F are stripped but NOT re-flowed. Those placeholders
expand at runtime to a pilot or ship name of unknown length; the shipped line
breaks already account for that and re-packing them to the column limit would
overflow for a long name.

Usage: debracket_stage.py <iso> <record> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
WIDTH, MAXLINES = 34, 3
OPEN, CLOSE = u"「", u"」"


def cols(s):
    return sum(2 if ord(c) > 0x7F else 1 for c in s)


def widest(t):
    return max(cols(l) for l in t.split(u"\n"))


def wrap(text, width):
    """Greedy column-aware wrap. Never splits a word."""
    out, line = [], u""
    for word in text.split():
        cand = word if not line else line + u" " + word
        if cols(cand) <= width:
            line = cand
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


# A break after one of these lands on a pause the reader already makes.
PUNCT = u".,!?;:…"
PUNCT_BONUS = 120       # worth about two columns of imbalance


def wrap_balanced(text, width):
    """Break into the fewest lines, evenly, preferring to break at a pause.

    A greedy fill packs the first line to the margin and leaves the last a stub
    - "Midgard! You were so slow, we came / to fetch you!". Simply evening the
    lines out fixes that but then splits clauses, turning
    "But are we sure about this...?" into "But are we sure about / this...?".

    So both goals at once, by dynamic programming over the word list: charge
    each line the square of its width, which is minimised when the lines are
    even, and refund PUNCT_BONUS when a line ends on punctuation. The greedy
    pass supplies the line count, which is already minimal.
    """
    words = text.split()
    if not words:
        return []
    greedy = wrap(text, width)
    if not greedy or len(greedy) < 2:
        return greedy
    n, want = len(words), len(greedy)
    seg = {}

    def span(i, j):
        if (i, j) not in seg:
            seg[(i, j)] = cols(u" ".join(words[i:j]))
        return seg[(i, j)]

    INF = float("inf")
    memo = {}

    def solve(i, k):
        """cheapest (cost, breaks) laying words[i:] into exactly k lines"""
        if (i, k) in memo:
            return memo[(i, k)]
        if i == n:
            out = (0, ()) if k == 0 else (INF, ())
        elif k == 0:
            out = (INF, ())
        else:
            out = (INF, ())
            for j in range(i + 1, n + 1):
                w = span(i, j)
                if w > width:
                    break
                c = w * w
                if words[j - 1][-1] in PUNCT:
                    c -= PUNCT_BONUS
                sub, tail = solve(j, k - 1)
                if sub is not INF and c + sub < out[0]:
                    out = (c + sub, (j,) + tail)
        memo[(i, k)] = out
        return out

    cost, breaks = solve(0, want)
    if cost is INF:
        return greedy
    lines, at = [], 0
    for b in breaks:
        lines.append(u" ".join(words[at:b]))
        at = b
    return lines


def convert(text):
    """Return the de-bracketed, re-wrapped field, or None to leave it alone."""
    if OPEN not in text:
        return None
    lines = text.split(u"\n")
    if len(lines) < 2:
        return None
    speaker, body = lines[0], lines[1:]
    # a choice menu carries several bracketed rows in one field; leave those,
    # they are a list, not a sentence, and re-flowing them would fuse the
    # options together
    if text.count(OPEN) > 1:
        return None
    joined = u" ".join(body).strip()
    if not (joined.startswith(OPEN) and joined.endswith(CLOSE)):
        return None
    inner = joined[1:-1].strip()
    if u"$" in text:
        # strip only: keep the shipped breaks, a placeholder may expand long
        stripped = [l.replace(OPEN, u"").replace(CLOSE, u"") for l in body]
        return speaker + u"\n" + u"\n".join(l for l in stripped if l.strip())
    got = wrap_balanced(inner, WIDTH)
    if not got or len(got) > MAXLINES:
        return None
    return speaker + u"\n" + u"\n".join(got)


def main():
    iso, rec = sys.argv[1], int(sys.argv[2])
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    hdr, data = live[rec]
    d = bytearray(data)
    done = kept = 0
    saved_b = saved_c = 0
    pos = 0
    while pos < len(d):
        z = bytes(d).find(b"\x00", pos)
        if z < 0:
            break
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        field = bytes(d[pos:z])
        if not field:
            pos = k
            continue
        try:
            text = field.decode("cp932")
        except UnicodeDecodeError:
            pos = k
            continue
        new = convert(text)
        if new is None or new == text:
            if OPEN in text:
                kept += 1
            pos = k
            continue
        nb = new.encode("cp932")
        slot = k - pos - 1
        if len(nb) > slot or widest(new) > WIDTH:
            kept += 1
            pos = k
            continue
        saved_b += len(field) - len(nb)
        saved_c += widest(text) - widest(new)
        d[pos:k] = nb + b"\x00" * (k - pos - len(nb))
        done += 1
        pos = k

    print("rec%d: %d row(s) de-bracketed, %d left as-is" % (rec, done, kept))
    print("       %d bytes and %d columns reclaimed" % (saved_b, saved_c))
    if write and done:
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % rec
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
