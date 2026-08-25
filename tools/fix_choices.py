# -*- coding: utf-8 -*-
"""Put each branch-choice option back on its own line.

The Japanese lays these out as four lines - speaker, prompt, then ONE LINE PER
OPTION:

    デンゼル
    「デンゼル選択」
    「１．コロニーから脱出する」
    「２．強奪されたガンダムを取り押さえる」

The translators wrote the options as running prose and let the wrap fall where
it may, so the game showed  "1. Escape the colony" "2. Recover / the stolen
Gundams"  - which reads as one sentence and pushes the second option off the
box. The player has to pick one of these, so the line structure is load-bearing,
not cosmetic.

Every replacement below stays inside the row's byte budget (checked before
writing). Also fixes rec142 row 299, which still had a Japanese 選択 in it.

Usage: fix_choices.py [--write]
"""
import importlib.util
import io
import json
import os
import sys

WORK = r"E:\Projects\SRW Z\_work"

# (record, row) -> the four lines, joined with real newlines
FIXED = {
    (2, 125): ['Denzel', '"Denzel\'s choice"',
               '"1. Escape the colony"', '"2. Recover the stolen Gundams"'],
    (7, 59): ['$n', '"$n\'s choice"',
              '"1. Hear the formation briefing"',
              '"2. Skip the formation briefing"'],
    (16, 37): ['Bello', '"Bello\'s choice"',
               '"1. Hear the formation briefing"',
               '"2. Skip the formation briefing"'],
    (35, 170): ['$n', '"$n\'s choice"',
                '"1. Join Sara\'s team"', '"2. Join Adette\'s team"'],
    (110, 679): ['Talia', '"Talia\'s choice"',
                 '"1. Fight as $c"', '"2. Return to ZAFT"'],
    (111, 787): ['Talia', '"Talia\'s choice"',
                 '"1. Fight as $c"', '"2. Return to ZAFT"'],
    (140, 454): ['Roger', '"Roger\'s choice"',
                 '"1. Forget and live in the city"',
                 '"2. Fulfill my duty"'],
    (142, 292): ['$n', '"$n\'s choice"',
                 '"1. Wish everything restored"',
                 '"2. Wish for world stability"'],
    (142, 299): ['$n', '"$n\'s choice"',
                 '"1. Wish for world stability"',
                 '"2. I can\'t decide myself"'],
    (147, 295): ['$n', '"$n\'s choice"',
                 '"1. Wish everything restored"',
                 '"2. Wish for world stability"'],
    (147, 300): ['$n', '"$n\'s choice"',
                 '"1. Wish for world stability"',
                 '"2. I can\'t decide myself"'],
    (154, 139): ['$n', '"$n\'s choice"',
                 '"1. Join the Pacific force"', '"2. Join the Garia force"'],
    (154, 170): ['$n', '"Rand\'s choice"',
                 '"1. Join the Pacific force"', '"2. Join the Garia force"'],
    # $n / $c expand to a name at runtime (up to ~8 characters), so these are
    # kept well under 32 to leave room for the substitution.
    (157, 24): ['Bright', '"Bright\'s choice"',
                '"1. Send $n to Gibraltar"',
                '"2. Put $n on patrol"'],
    (160, 57): ['$n', '"$n\'s choice"',
                '"1. Search for Renton"', '"2. Stay behind"'],
}

MAXCOL = 32          # narrowest measured row width (see srvc_refit.SCREEN_COLS:
                     # a wide speaker portrait pushes the box right and steals
                     # columns, so 32 is the safe figure, not 37)


def main():
    write = "--write" in sys.argv
    by_rec = {}
    for (rec, row), lines in FIXED.items():
        by_rec.setdefault(rec, {})[row] = "\n".join(lines)

    total = bad = 0
    for rec, rows in sorted(by_rec.items()):
        f = os.path.join(WORK, "tools", "rec%03d_en.py" % rec)
        sj = os.path.join(WORK, "analysis", "rec%03d_script.json" % rec)
        spec = importlib.util.spec_from_file_location("m", f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        script = json.load(io.open(sj, encoding="utf-8"))
        src = io.open(f, encoding="utf-8").read()

        for row, new in sorted(rows.items()):
            old = m.T.get(row)
            budget = script[row]["budget"]
            nb = len(new.encode("cp932", "replace"))
            wide = [l for l in new.split("\n") if len(l) > MAXCOL]
            status = "ok"
            if nb > budget:
                status = "OVER BUDGET %d > %d" % (nb, budget)
                bad += 1
            elif wide:
                status = "row over %d cols: %r" % (MAXCOL, wide[0])
                bad += 1
            print("rec%03d row %-4d %3d/%3d bytes  %s" % (rec, row, nb, budget, status))
            if old is None:
                print("   !! row not present in T")
                bad += 1
                continue
            if status != "ok":
                continue
            a = repr(old)
            b = repr(new)
            if a in src:
                src = src.replace(a, b, 1)
                total += 1
            else:
                print("   !! could not locate the source literal")
                bad += 1

        if write:
            io.open(f, "w", encoding="utf-8").write(src)

    print("\nrewrote %d rows%s; %d problems"
          % (total, "" if write else " (dry run)", bad))
    if not write:
        print("(pass --write to apply)")


if __name__ == "__main__":
    main()
