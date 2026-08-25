# -*- coding: utf-8 -*-
"""Re-wrap battle captions to the caption box, now that length is free.

The Japanese source tops out at 38 columns per line (a sharp cliff after it:
1,221 lines at 38, then 50 at 40 and one each at 42/44/48), so 38 is the box.
English is far shorter than Japanese, so most captions inherited a line break
they no longer need - 8,324 of 12,360 broken captions fit on ONE line.

Three fixes, all content-preserving (only whitespace/breaks change):
  1. break unnecessary  -> join onto one line
  2. break leaves an orphan ("Hmph, I see... / You!") -> re-split balanced,
     so the two lines are close in width instead of 14 + 4
  3. no break but wider than the box -> split (these clip on screen today)

A half-width character is 1 column; fullwidth is 2. Our private digits and
periods (encode mode "menuhw") render half-width, and the ellipsis U+2026 is
one fullwidth glyph.
"""
import io
import json
import sys

NL = chr(92) + "n"
WIDTH = 38


def cols(s):
    return sum(1 if ord(c) < 0x80 or c == "\u2026" else 2 for c in s)


def split_balanced(text, width=WIDTH):
    """Fewest lines; among those, the most even split."""
    words = text.split(" ")
    if cols(text) <= width:
        return [text]
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        ca, cb = cols(a), cols(b)
        if ca <= width and cb <= width:
            score = abs(ca - cb)
            if best is None or score < best[0]:
                best = (score, [a, b])
    if best:
        return best[1]
    # needs three lines - greedy, then balance the tail
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cols(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    path = "analysis/srvc_en.json"
    en = json.load(io.open(path, encoding="utf-8"))
    joined_n = resplit_n = split_n = 0
    for k, v in list(en.items()):
        if not isinstance(v, str):
            continue
        parts = [p.strip() for p in v.split(NL)]
        flat = " ".join(p for p in parts if p)
        new = split_balanced(flat)
        out = NL.join(new)
        if out == v:
            continue
        if len(parts) > 1 and len(new) == 1:
            joined_n += 1
        elif len(parts) > 1:
            resplit_n += 1
        else:
            split_n += 1
        en[k] = out
    json.dump(en, io.open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print("captions joined onto one line : %s" % "{:,}".format(joined_n))
    print("breaks re-balanced            : %s" % "{:,}".format(resplit_n))
    print("over-wide captions split      : %s" % "{:,}".format(split_n))
    over = sum(1 for v in en.values() if isinstance(v, str)
               and any(cols(l) > WIDTH for l in v.split(NL)))
    print("captions still over %d columns : %d" % (WIDTH, over))


if __name__ == "__main__":
    main()
