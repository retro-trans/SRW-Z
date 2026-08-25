# -*- coding: utf-8 -*-
"""Re-translate the battle lines that overflow the box, with per-line budgets.

WHAT THE FIRST PASS GOT WRONG: it used a flat 48-column limit taken from the
single longest Japanese segment in the whole file, and it explicitly allowed the
model to drop the Japanese line break. Both are too loose. A line can pass a
48-column check and still be far wider than the box ever draws at that spot, and
collapsing a two-row Japanese quote into one English row doubles its width.

WHAT THE BOX ACTUALLY DOES (measured from a save state taken with a quote on
screen, analysis/_ee6.bin):
  - The drawn text lives at 0x005FDDB8, with the speaker name in a 24-byte field
    at 0x005FDDA0 ("Duke"). The buffer holds EXACTLY what is on screen.
  - The literal backslash-n we store is converted to a real 0x0A there, so the
    game does honour our break marker.
  - Duke's second row ran from x=160 to the screen edge at 640 = 480px for 37
    characters, i.e. the fixed 13px advance (BHOOK writes destW=12, SADV returns
    12+1) and ~37 characters of usable width.
  - Only 2 text rows are visible; a quote needing a third scrolls, and the front
    of the buffer is consumed - which is why the player sees a fragment.

THE RULE USED HERE: never draw wider than the Japanese did, capped at the
measured screen width. budget = min(37, 2 * longest_japanese_segment), because
Japanese is fullwidth at 2 columns per character and the original demonstrably
fits. Rows are capped at 2, or the Japanese's own row count if that is greater.

Usage: srvc_refit.py [rounds]
"""
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call
from srvc_deepseek import norm, parse_map, load_gloss, chunk_gloss

WORK = r"E:\Projects\SRW Z\_work"
# Usable width VARIES WITH THE SPEAKER'S PORTRAIT: the box starts to the right
# of it, so a wide portrait steals columns. Measured two cases at the fixed 13px
# advance:
#   Duke/Grendizer (narrow face) - text x=160..640 = 480px = 37 chars
#   King Vega      (wide face)   - text x=205..635 = 430px = 33 chars, and the
#                                  33rd character is clipped by the border
# Toby's line independently broke at exactly 32. So 32 is the safe width - it is
# the narrowest case, and a short line merely leaves space to its right.
SCREEN_COLS = 32
MAXROWS = 2
CHUNK = 10
WORKERS = 8

SYSTEM = """You translate BATTLE VOICE lines for an English fan-translation of the PS2 game Super Robot Taisen Z - the short shouts a pilot makes while attacking or being hit, shown in a small box during the battle animation.

THE BOX IS SMALL. Each line below comes with a MAX character count for one row. This is a hard limit measured from the game: text past it runs off the screen and the player never sees it.

RULES - follow exactly:
1. Each line: at most 2 rows. Separate rows with a literal backslash followed by n. EACH row must be at most the MAX given for that line. Count the characters.
2. PURE ASCII, and only these characters: letters, digits, space, and . , ! ? ' " -
   No colons, no parentheses, no tildes, no em dashes, no ellipsis character (use ...).
3. Do NOT add surrounding quote marks - the game draws those itself.
4. NAMES AND ATTACKS: use the glossary spellings given below EXACTLY.
5. These are shouted in combat: punchy and idiomatic, not literal prose. Keep the exclamation marks. Match the speaker's tone.
6. FITTING IS MANDATORY. If the natural English is too long, cut it down - drop adjectives, use a shorter synonym, compress the phrasing. A shout that overruns is thrown away and stays Japanese, which is worse than a terse one.

OUTPUT: a single JSON object mapping each id (as a string) to its translated line. No commentary, no code fences."""


def budgets(jp):
    """(chars per row, max rows) - THE MEASURED BOX, not the Japanese width.

    An earlier version returned min(37, 2 * longest Japanese segment) on the
    reasoning that the original demonstrably fits. That was a proxy adopted
    before the box could be measured, and it is far too strict: a 4-character
    Japanese shout like 任せろ！ yields an 8-column budget, which no English
    equivalent can meet, and the wrapper then produces nonsense like
    "Leave it to / me!". The box is 37 columns wide whatever the Japanese did,
    so a short line simply leaves space to its right.

    Rows stay at 2 unless the Japanese itself used more - if the original
    scrolls, we are no worse than the original.
    """
    return SCREEN_COLS, max(MAXROWS, len(jp.split("\\n")))


def fits(v, cols, rows):
    if not v or not v.strip():
        return "empty"
    if any(ord(c) > 126 for c in v):
        return "non-ascii"
    segs = v.split("\\n")
    if len(segs) > rows:
        return "%d rows" % len(segs)
    for s in segs:
        if len(s) > cols:
            return "row of %d > %d" % (len(s), cols)
    return None


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))
    by = {str(x["i"]): x for x in items}
    p = os.path.join(WORK, "analysis", "srvc_en.json")
    en = json.load(io.open(p, encoding="utf-8"))

    def overflowing():
        out = []
        for k, v in en.items():
            cols, rows = budgets(by[k]["jp"])
            if fits(v, cols, rows):
                out.append(k)
        return out

    todo = overflowing()
    print("%s of %s entries overflow the box"
          % ("{:,}".format(len(todo)), "{:,}".format(len(en))))

    gloss = load_gloss()
    api = open(KEYFILE).read().strip()
    lock = threading.Lock()

    for rnd in range(rounds):
        todo = overflowing()
        if not todo:
            break
        print("round %d: %s to refit" % (rnd + 1, "{:,}".format(len(todo))))
        chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
        fixed = [0]
        done = [0]

        def do(ch):
            lines = [by[k]["jp"] for k in ch]
            g = chunk_gloss(gloss, lines)
            user = ""
            if g:
                user += ("GLOSSARY (use these spellings exactly):\n" +
                         "\n".join(g) + "\n\n")
            user += "Translate each line. id<TAB>MAX<TAB>japanese\n"
            for k in ch:
                cols, _ = budgets(by[k]["jp"])
                user += "%s\t%d\t%s\n" % (k, cols, by[k]["jp"])
            try:
                r = parse_map(call(api, SYSTEM, user))
            except Exception:
                r = {}
            got = {}
            for k in ch:
                v = r.get(k)
                if not isinstance(v, str):
                    continue
                v = norm(v)
                cols, rows = budgets(by[k]["jp"])
                if not fits(v, cols, rows):
                    got[k] = v
            with lock:
                en.update(got)
                fixed[0] += len(got)
                done[0] += 1
                if done[0] % 25 == 0 or done[0] == len(chunks):
                    json.dump(en, io.open(p, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=1)
                    print("   %d/%d chunks | refitted %s"
                          % (done[0], len(chunks), "{:,}".format(fixed[0])))

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(en, io.open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if not fixed[0]:
            break

    left = overflowing()
    print("done: %s still overflowing" % "{:,}".format(len(left)))


if __name__ == "__main__":
    main()
