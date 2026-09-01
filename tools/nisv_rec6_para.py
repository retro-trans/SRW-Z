# -*- coding: utf-8 -*-
"""Group rec6's positioned runs back into paragraphs, and lay them out again.

See nisv_rec6.py for the container format.  A paragraph is the run of visual
lines that make up one block of prose:

    first_x  x of the FIRST line (the japanese indents it, e.g. 38 vs 19)
    cont_x   x of every following line
    y        y of the first line
    attr     base attribute (0 plain, 6 title, 3 pros bullet, 7 cons bullet)
    lines    the original visual lines, as authored
    text     those lines joined - the thing we translate

Inline attribute changes are marked {a=NN}...{/a}: 0e is a highlighted
keyword sitting inside a sentence, 03/07 are the bullets that share a line
with their 長所 / 短所 label.

The renderer does no wrapping, so laying english out is our job: wrap to the
panel, keep each paragraph at its authored y, and push the rest of the page
down only when a paragraph genuinely grew.
"""
import re
import unicodedata

from nisv_rec6 import LINE_H, Run

KW = 0x0e
RIGHT = 532                # right edge of the panel, measured from the japanese

# This panel does NOT use the menu metrics (21px full / 13px half).  Every
# tight inline pair in the japanese advances exactly 19px per full-width
# character - 601 of the 750 measurable pairs, the rest being deliberate
# column gaps.  Note that …  ▼  ※  →  ×  ↓  ± all advance 19 here, so width
# is decided by "is it ASCII", not by east_asian_width (which calls several
# of them ambiguous).
#
# No original run contains a half-width character - every ASCII byte in rec6
# came from our own in-place patches - so W_HALF cannot be measured the same
# way.  It is 12 because that is what our OWN renderer hook forces: the SADV
# hook in patch_hwfont.py pins the destination advance to a constant 12 for
# the half-width code range and for space.  rec5, the already-shipped sibling
# record, proves this panel goes through that path - its ASCII renders
# half-width, and it needed the 0x2E-0x3D fullwidth workaround that is
# specific to the same 0x13A290 reader.
W_FULL, W_HALF = 19, 12

# A line can only be a CONTINUATION of the one above it if that line actually
# reached the right margin - the renderer never wraps early.  Measuring every
# y+11 transition in the japanese gives a cleanly bimodal answer: real wraps
# stop 0/19/38/57px short of the margin (945 of them), and everything that is
# really a new block stops 76px or more short (250).  60 sits in the gap.
# Without this, a short table cell swallows the next row's label as its second
# line and shunts the rest of the page down.
WRAP_SLACK = 60

# Labels we ourselves patched into rec6 in place, and the pixel width of the
# japanese each replaced (小隊攻撃 / 援護攻撃 / 援護防御 = 4 cells, 反撃 = 2).
# Needed only when reading a disc we have already patched; once a section is
# retranslated its runs are re-emitted consistently and this stops mattering.
PATCHED = {"Sq Atk": 76, "Sup Atk": 76, "Sup Def": 76, "Ctr": 38}

# How far a continuation line may sit from its paragraph's first line.  Across
# the whole book genuine wraps take exactly four values: -19 (body text, whose
# first line is indented), 0 (a table's description column wrapping onto
# itself), +19 (bullets) and +76 (a hanging indent aligned to an inline span) -
# 393 cases.  The one paragraph outside that range is a short table cell at
# x=475 that happens to end on the margin, so `filled` cannot tell that the
# next row's label at x=57 is not its continuation.
INDENT_LO, INDENT_HI = -38, 95

_SPAN = re.compile(r"\{a=([0-9a-f]{2})\}(.*?)\{/a\}", re.S)


def px(s):
    # ASCII is half-width EXCEPT 0x2E-0x3D, which the menu encoder rewrites to
    # their fullwidth forms because they are control codes to this reader - so
    # a digit or a full stop costs 19px in english, not 13.
    return sum(W_HALF if ord(c) < 128 and not (0x2E <= ord(c) <= 0x3D)
               else W_FULL for c in s)


def strip(text):
    """The text as it will be drawn, markers removed."""
    return _SPAN.sub(lambda m: m.group(2), text)


class Para(object):
    __slots__ = ("kind", "attr", "first_x", "cont_x", "y", "lines", "sep")

    def __init__(self, kind, attr, first_x, cont_x, y, lines, sep=""):
        self.kind, self.attr = kind, attr
        self.first_x, self.cont_x, self.y = first_x, cont_x, y
        self.lines, self.sep = lines, sep

    @property
    def text(self):
        return self.sep.join(self.lines)

    def __repr__(self):
        return "Para(a=%#04x,x=%d/%d,y=%d,%r)" % (
            self.attr, self.first_x, self.cont_x, self.y, self.text)


def _ascii(run):
    return any(ord(c) < 128 for c in run.text)


def _mark(run, base):
    if run.attr != base:
        return "{a=%02x}%s{/a}" % (run.attr, run.text)
    return run.text


def group(runs):
    """[Run] -> [Para].

    Two runs can share a y for different reasons, and they are not the same
    thing.  A run starting exactly where the previous one ended is a TIGHT
    inline span - a highlighted keyword inside a sentence - and folds into the
    text.  A run starting further right sits on a FIXED COLUMN (the bullets at
    x=95 beside their 長所 label at x=38) and stays its own paragraph, so that
    translating the label cannot drag the column with it.
    """
    paras, cur, prev, cursor = [], None, None, 0
    for r in runs:
        tight = prev is not None and r.y == prev.y and r.x == cursor
        if prev is not None and r.y == prev.y and not tight:
            w = PATCHED.get(prev.text)
            if w is not None:
                # prev is one of OUR earlier in-place patches, so its measured
                # width no longer matches the japanese that the following run's
                # x was authored against.  Measure against the width of the
                # japanese it replaced instead: every tight case in the book
                # lands exactly on it, and the three that do not (95px) are
                # real column anchors.
                tight = r.x - prev.x == w
        filled = cursor >= RIGHT - WRAP_SLACK
        if (prev is None or r.kind == 4 or prev.kind == 4
                or r.y > prev.y + LINE_H
                or (r.y == prev.y and not tight)):
            cur = Para(r.kind, r.attr, r.x, r.x, r.y, [_mark(r, r.attr)])
            paras.append(cur)
        elif tight:
            cur.lines[-1] += _mark(r, cur.attr)
        elif not filled:
            # the line above stopped well short of the margin, so this cannot
            # be a wrap - it is a new block (a table row, a fresh sentence)
            cur = Para(r.kind, r.attr, r.x, r.x, r.y, [_mark(r, r.attr)])
            paras.append(cur)
        elif (len(cur.lines) == 1
                and INDENT_LO <= r.x - cur.first_x <= INDENT_HI
                and (r.x != cur.first_x or r.attr == prev.attr)):
            # Second line sets the continuation column, which may be the SAME
            # as the first line's: a definition table's description column
            # (term at x=38, text at x=95) wraps onto itself, and splitting
            # there would cut a sentence in half for the translator.
            #
            # When the x is unchanged, the ATTRIBUTE decides: a genuine wrap
            # carries the open span across the break (03 -> 03), while the
            # next ROW of a table starts back at the base attribute
            # (03 -> 00), as 攻撃時：/防御時： rows do.
            cur.cont_x = r.x
            cur.lines.append(_mark(r, cur.attr))
        elif len(cur.lines) > 1 and r.x == cur.cont_x:
            cur.lines.append(_mark(r, cur.attr))
        else:
            # re-indented to the first-line column: a new paragraph starting
            # on the very next line, not a continuation of this one.
            cur = Para(r.kind, r.attr, r.x, r.x, r.y, [_mark(r, r.attr)])
            paras.append(cur)
        cursor = r.x + px(r.text)
        prev = r
    return paras


def _spans(line, base):
    out, i = [], 0
    for m in _SPAN.finditer(line):
        if line[i:m.start()]:
            out.append((base, line[i:m.start()]))
        out.append((int(m.group(1), 16), m.group(2)))
        i = m.end()
    if line[i:]:
        out.append((base, line[i:]))
    return out


def _rebalance(lines):
    """Close and reopen spans that a line break fell inside.

    Wrapping splits on spaces, so a span whose text contains a space can open
    on one line and close on the next.  _spans() only matches a complete
    {a=NN}...{/a} within one line, so an unbalanced line would draw its
    markers as literal text.  Spans never nest, so the last unmatched opener
    is all we have to track.
    """
    out, carry = [], None
    for ln in lines:
        s = ("{a=%02x}" % carry if carry is not None else "") + ln
        o, c = s.rfind("{a="), s.rfind("{/a}")
        if o > c:
            carry = int(s[o + 3:o + 5], 16)
            s += "{/a}"
        else:
            carry = None
        out.append(s)
    return out


def wrap(p, right=RIGHT):
    """Word-wrap one paragraph's text to the panel; -> marked-up lines."""
    out, line = [], ""
    for w in p.text.split(" "):
        cand = w if not line else line + " " + w
        lim = right - (p.first_x if not out else p.cont_x)
        if line and px(strip(cand)) > lim:
            out.append(line)
            line = w
        else:
            line = cand
    if line:
        out.append(line)
    return _rebalance(out)


COL_GAP = 12               # smallest gap we leave between two columns


def avoid_collisions(paras, lines_for, right=RIGHT, rounds=3):
    """Push shared columns right so english terms cannot overrun them.

    A definition table puts its term at x=38 and its description at x=133,
    which fitted the japanese (連携攻撃 is 76px) but not "Focused Atk" at
    132px - the term would be drawn straight over the description.

    The description column is shared by every row of the table, so it has to
    move as a unit; moving one row would leave the table ragged.  Widening a
    column narrows it, which can rewrap a row and lengthen another term, so
    this repeats until it settles.
    """
    moved = {}
    for _ in range(rounds):
        ends, by_y = {}, {}
        for p in paras:
            lines = lines_for(p)
            ends[id(p)] = p.first_x + (px(strip(lines[0])) if lines else 0)
            by_y.setdefault(p.y, []).append(p)
        need = {}
        for group in by_y.values():
            group.sort(key=lambda q: q.first_x)
            for a, b in zip(group, group[1:]):
                want = ends[id(a)] + COL_GAP
                if want > b.first_x:
                    need[b.first_x] = max(need.get(b.first_x, 0), want)
        if not need:
            break
        for p in paras:
            new = need.get(p.first_x)
            if new is None or new >= right:
                continue
            if p.cont_x == p.first_x:
                p.cont_x = new
            moved[p.first_x] = new
            p.first_x = new
    return moved


def place(paras, lines_for):
    """[Para] -> [Run].  `lines_for(p)` supplies the visual lines.

    A paragraph keeps its authored y; the page is pushed down only where one
    grew, and paragraphs that share a y (a label beside its heading) move
    together.
    """
    runs, shift = [], 0
    for i, p in enumerate(paras):
        y0 = p.y + shift
        lines = lines_for(p)
        for n, ln in enumerate(lines):
            x = p.first_x if n == 0 else p.cont_x
            for attr, txt in _spans(ln, p.attr):
                if txt:
                    runs.append(Run(p.kind, attr, x, y0 + n * LINE_H, 1, txt))
                    x += px(txt)
        bottom = y0 + len(lines) * LINE_H
        if i + 1 < len(paras) and paras[i + 1].y > p.y:
            gap = paras[i + 1].y + shift
            if gap < bottom:
                shift += bottom - gap
    return runs


def identity(paras):
    """Re-emit using the authored line breaks - must reproduce the input."""
    return place(paras, lambda p: p.lines)


def layout(paras, right=RIGHT):
    """Re-emit with english word-wrapping."""
    return place(paras, lambda p: wrap(p, right))
