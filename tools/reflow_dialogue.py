# -*- coding: utf-8 -*-
"""Re-wrap translated dialogue to the real message-box width.

The translations inherited the JAPANESE line breaks. Japanese glyphs are
fullwidth; our English is half-width, so each line only used about half the box
and long lines spilled onto a 4th row that the box cannot show (measured from a
screenshot: 27.5 px per half-width char, 1055 px of text area = 38 chars, and 3
visible body lines).

This re-wraps each row's body to WIDTH chars, at most MAXLINES lines. Wrapping
wider can only remove newlines, so a row's byte count never grows - but every
row is still checked against its cp932 budget and left alone if it would not
fit. Speaker line, placeholders ($n/$c/$F/$f) and non-ASCII rows (scene headers,
untranslated Japanese) are preserved untouched.

Usage: reflow_dialogue.py [--apply] [recN ...]
"""
import glob, json, os, re, sys
import importlib.util as u

WORK = r"E:\Projects\SRW Z\_work"
WIDTH = 37          # widest wrap; only used when nothing narrower fits 3 lines
SAFE_WIDTH = 34     # what the box REALLY shows (in-game capture clipped at 34)
MAXLINES = 3
# NOTE: a portrait screenshot appeared to clip a 34-char line, which would argue
# for ~31. But narrowing to 31 pushes rows needing a 4th (invisible) row from 545
# to 3757 - seven times worse - and that screenshot's frame ran to the image edge
# with no letterbox, unlike others, so it was probably a cropped capture rather
# than real clipping. Do not narrow this without confirming in-game first.


def bl(s):
    return len(s.encode("cp932", "replace"))


# Runtime placeholders. These are 2 bytes in the data but the engine expands
# them to a NAME before drawing, so wrapping on the literal text under-measures
# the rendered line and it overruns the box: "Idiot! Stop, $n! He's way out of"
# is 32 columns stored but 37 drawn, and clipped mid-word in-game.
PLACEHOLDER = {"$n": 7, "$c": 7, "$F": 7, "$f": 7}


def vislen(s):
    """Rendered column count, counting placeholders at their expanded width."""
    for k, v in PLACEHOLDER.items():
        s = s.replace(k, "X" * v)
    return len(s)


def wrap(text, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if not cur:
            cur = w
        elif vislen(cur) + 1 + vislen(w) <= width:
            cur += " " + w
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def reflow(t):
    """Return the re-wrapped string, or None to leave the row alone."""
    parts = t.split("\n")
    if len(parts) < 2:
        return None                      # speaker-only / single line
    speaker, body = parts[0], parts[1:]
    joined = " ".join(x.strip() for x in body).strip()
    if not joined:
        return None
    if any(ord(c) > 0x7E for c in joined):
        return None                      # scene header / still Japanese
    joined = re.sub(r"\s+", " ", joined)
    # The box actually shows ~34 columns, not WIDTH: an in-game capture clipped
    # Toby's line at exactly 34 ("...He's way ou|"). But wrapping EVERYTHING to
    # 34 pushes rows needing an invisible 4th line from 551 to 1652 - trading a
    # few clipped characters for whole lost lines, which is worse.
    # So pick the NARROWEST width that still fits in MAXLINES for THIS row, and
    # only fall back to the wider (clipping) wrap when nothing else fits. Rows
    # that still need a 4th line at WIDTH are too long to wrap out of trouble
    # and need SHORTENING - tracked separately.
    lines = None
    for w in range(SAFE_WIDTH, WIDTH + 1):
        cand = wrap(joined, w)
        if len(cand) <= MAXLINES:
            lines = cand
            break
    if lines is None:
        lines = wrap(joined, WIDTH)
    if lines == [x.strip() for x in body]:
        return None                      # already optimal
    return speaker + "\n" + "\n".join(lines)


def main():
    apply = "--apply" in sys.argv
    ids = [int(a[3:]) if a.startswith("rec") else int(a)
           for a in sys.argv[1:] if a != "--apply"]
    files = ([os.path.join(WORK, "tools", "rec%03d_en.py" % n) for n in ids] if ids
             else sorted(glob.glob(os.path.join(WORK, "tools", "rec*_en.py"))))
    tot = changed = overlong_before = overlong_after = skipped_budget = 0
    for p in files:
        n = int(os.path.basename(p)[3:6])
        wk_path = os.path.join(WORK, "analysis", "rec%03d_work.json" % n)
        if not os.path.exists(wk_path):
            continue
        wk = {r["i"]: r for r in json.load(open(wk_path, encoding="utf-8"))}
        spec = u.spec_from_file_location("m%d" % n, p)
        m = u.module_from_spec(spec); spec.loader.exec_module(m)
        T = dict(m.T)
        dirty = False
        for i, t in list(T.items()):
            tot += 1
            if len(t.split("\n")) - 1 > MAXLINES:
                overlong_before += 1
            new = reflow(t)
            if new is None:
                continue
            bud = wk.get(i, {}).get("budget")
            if bud is not None and bl(new) > bud:
                skipped_budget += 1
                continue
            T[i] = new
            dirty = True
            changed += 1
            if len(new.split("\n")) - 1 > MAXLINES:
                overlong_after += 1
        if apply and dirty:
            lines = ["# -*- coding: utf-8 -*-",
                     '"""Stage record %d dialogue (re-wrapped to box width)."""' % n,
                     "", "T = {"]
            for k in sorted(T):
                lines.append("    %d: %r," % (k, T[k]))
            lines.append("}")
            open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("rows: %d | re-wrapped: %d | skipped (budget): %d" % (tot, changed, skipped_budget))
    print("rows exceeding %d body lines: %d -> %d" % (MAXLINES, overlong_before, overlong_after))
    print("APPLIED" if apply else "(dry run - pass --apply to write)")


if __name__ == "__main__":
    main()
