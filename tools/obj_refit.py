# -*- coding: utf-8 -*-
"""Shorten mission-objective / SR-point strings that do not fit their field.

Two failure modes seen in v1.31, both silent:
  - OVER BUDGET: apply_stage skips the field and it stays Japanese (111 slots).
  - EXACT FILL: the field is NUL-TERMINATED, so writing exactly `budget` bytes
    leaves no terminator and the renderer runs into the next field, which is how
    "Annihilate all enemies。Defeat Shinn or Alex。" ended up on one line
    (43 slots). apply_stage now requires len < budget, so these need shortening
    too or they would simply revert to Japanese.

Budgets are BYTES AFTER MENU ENCODING, where every digit and . : ; < = / turns
FULLWIDTH and costs 2 - so dropping a trailing full stop buys 2 bytes, and a
turn count costs 2 rather than 1. A string can appear at several offsets with
different slot sizes; the smallest one wins.

Deterministic rewrites are tried first (they handle the formulaic majority);
anything still too long goes to DeepSeek with its exact byte budget.

Usage: obj_refit.py [--write]
"""
import io
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import encode as pencode
from zkn_deepseek import KEYFILE, call
from srvc_deepseek import parse_map, sanitize

WORK = r"E:\Projects\SRW Z\_work"
WORKERS = 8
CHUNK = 8

# cheap, safe rewrites, applied in order until it fits
RULES = [
    (re.compile(r"\.$"), ""),                       # trailing stop: 2 bytes
    (re.compile(r"\bAnnihilate\b"), "Destroy"),
    (re.compile(r"\bwithin\b"), "in"),
    (re.compile(r"\breinforcements\b"), "reinforcements"),
    (re.compile(r"\bmeet the victory conditions\b"), "meet victory"),
    (re.compile(r"\bmeet victory conditions\b"), "meet victory"),
    (re.compile(r"\bthe map's\b"), "the"),
    (re.compile(r"\ball other enemies\b"), "all others"),
    (re.compile(r"\bAny ally unit destroyed\b"), "An ally is destroyed"),
    (re.compile(r"\bappearing\b"), "appearance"),
    (re.compile(r"\s+"), " "),
]

SYSTEM = """You shorten mission-objective lines for an English fan-translation of Super Robot Taisen Z.

Each line comes with a MAX byte count. This is a hard field size in the game: a line that exceeds it is thrown away and the objective stays in Japanese.

HOW BYTES ARE COUNTED: ordinary letters, spaces and most punctuation cost 1 byte. But every DIGIT and every one of . : ; < = / costs TWO bytes, because the menu renderer needs them fullwidth. So "3 turns." costs 2+1+5+2 = 10, not 8. Dropping a trailing full stop saves 2 bytes.

RULES:
1. Keep the meaning exactly - these are win/lose conditions and the player relies on them. Never change a number, a name, or the logic (and/or).
2. Use ASCII only, and only these characters: letters, digits, space, and . , ! ? ' " -
3. Keep each display row at most 36 characters. Use a real newline to break a longer condition across rows.
4. Terse imperative style is fine and expected: "Destroy all enemies in 3 turns" reads perfectly well.
5. Do not add a trailing full stop unless it fits.

OUTPUT: a single JSON object mapping each id (as a string) to the shortened line. No commentary, no code fences."""


# Slots the model could not squeeze into, hand-written. Note a Japanese string
# can occupy several slots of different sizes and apply_stage keys by the
# Japanese, so the SMALLEST slot governs - which is why a few of these read
# tighter than the roomiest place they appear.
MANUAL = {
    "All allies destroyed.": "All allies lost",
    "Gainer Rescue Team": "Gainer Rescue",
    "Rescue the prisoners.": "Free prisoners",
    "Annihilate all enemies": "Destroy enemies",
    "Annihilate all enemies.": "Destroy enemies",
    "Survive to turn 6 after Ginga-Goh appears.":
        "Survive 6 turns after Ginga-Goh",
    "Annihilate all enemies within 3 turns of reinforcements.":
        "Destroy enemies 3 turns after reinforcements",
    "Annihilate all enemies within 4 turns after reinforcements.":
        "Destroy enemies 4 turns after reinforcements",
    "Ally battleship destroyed.": "Ally battleship lost",
    "Ally battleship or Harry destroyed.": "Ally battleship or Harry lost",
    "Annihilate the Shadow Angels.": "Destroy Shadow Angels",
    "Shadow Angels reach the map's west edge.":
        "Shadow Angels reach west edge",
    "Breach the enemy defense line.": "Breach the defense line",
    "All allies destroyed": "All allies lost",
    "Survive to turn 3 after entering the closed space.":
        "Survive 3 turns in the closed space",
    "Defeat all enemies before the Artificial Sun.":
        "Defeat enemies before Artificial Sun",
}


# The Operation End panel clips well before the screen edge: in the Ep.3 capture
# the SR line ran to x=640 (screen) while the panel border sat near x=588, i.e.
# ~38 characters of usable width at the fixed 13px advance. 36 leaves a margin.
# Fitting the BYTE budget is not enough on its own - a 60-byte string is one
# 58-column line and runs straight out of the panel.
OBJ_COLS = 36


def enc_len(s):
    return len(pencode(s, "menu"))


def disp_cols(s):
    """On-screen width of one row.

    Menu encoding turns every digit and . : ; < = / FULLWIDTH, and a fullwidth
    glyph is TWO columns wide while remaining one character in this string. So
    "within 4 ally phases" measures 20 in Python and 21 on screen.
    """
    return sum(2 if 0x2E <= ord(c) <= 0x3D else 1 for c in s)


def wrap_cols(s, limit, cols=OBJ_COLS):
    """Re-flow the whole string to `cols`, keeping under the byte budget.

    The existing newlines are treated as soft wrapping, not structure - the
    Japanese breaks these mid-sentence purely to fit - so they are joined first
    and the text re-wrapped as one flow. Wrapping each existing line separately
    leaves orphans: "...or\\nshoot\\ndown Sting..." instead of clean rows.
    """
    out, cur = [], ""
    for w in s.split():
        cand = w if not cur else cur + " " + w
        if disp_cols(cand) <= cols:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    if any(disp_cols(x) > cols for x in out):
        return None                       # a single word wider than the panel
    r = "\n".join(out)
    return r if enc_len(r) < limit else None


def load():
    jp = json.load(io.open(os.path.join(WORK, "analysis", "objectives_jp.json"),
                           encoding="utf-8"))
    en = json.load(io.open(os.path.join(WORK, "analysis", "objectives_en.json"),
                           encoding="utf-8"))
    budget = {}
    for j, locs in jp.items():
        budget[j] = min(b for _, _, b in locs)
    return jp, en, budget


def try_rules(s, limit):
    if enc_len(s) < limit:
        return s
    for pat, rep in RULES:
        s2 = pat.sub(rep, s).strip()
        if s2 and s2 != s:
            s = s2
            if enc_len(s) < limit:
                return s
    return s


def main():
    write = "--write" in sys.argv
    jp, en, budget = load()

    # PASS 1: wrap everything to the panel width. Purely mechanical, no meaning
    # lost, and it is what was missing in v1.31 - strings that fitted their byte
    # budget as one 58-column line still ran out of the panel.
    wrapped = 0
    for j, e in list(en.items()):
        b = budget.get(j)
        if b is None:
            continue
        # Re-flow UNCONDITIONALLY. Checking "is any row too wide?" first misses
        # strings that are merely wrapped badly - an earlier pass left
        # "...or\nshoot\ndown Sting..." whose orphan rows are all short enough to
        # pass a width test while looking broken on screen.
        w = wrap_cols(e, b)
        if w and w != e:
            en[j] = w
            wrapped += 1
    print("wrapped to %d columns: %d strings" % (OBJ_COLS, wrapped))

    todo = {}
    for j, e in en.items():
        b = budget.get(j)
        if b is None:
            continue
        # too many bytes for the slot, or still too wide for the panel
        if enc_len(e) >= b or any(disp_cols(p) > OBJ_COLS for p in e.split("\n")):
            todo[j] = (e, b)
    print("%d strings still do not fit" % len(todo))

    fixed, still = {}, {}
    for j, (e, b) in todo.items():
        s = MANUAL.get(e, e)
        if enc_len(s) >= b:
            s = try_rules(s, b)
        if enc_len(s) < b:
            fixed[j] = s
        else:
            still[j] = (e, b)
    print("  deterministic rules fixed %d, %d left for the model"
          % (len(fixed), len(still)))

    if still:
        api = open(KEYFILE).read().strip()
        keys = list(still)
        idx = {str(i): k for i, k in enumerate(keys)}
        chunks = [keys[i:i + CHUNK] for i in range(0, len(keys), CHUNK)]
        lock = threading.Lock()
        rev = {k: str(i) for i, k in enumerate(keys)}

        def do(ch):
            user = "Shorten each line. id<TAB>MAXBYTES<TAB>english\n"
            for k in ch:
                e, b = still[k]
                user += "%s\t%d\t%s\n" % (rev[k], b - 1, e)
            try:
                r = parse_map(call(api, SYSTEM, user))
            except Exception:
                r = {}
            got = {}
            for k in ch:
                v = r.get(rev[k])
                if not isinstance(v, str):
                    continue
                v = sanitize(v).strip()
                if v and enc_len(v) < still[k][1]:
                    got[k] = v
            with lock:
                fixed.update(got)

        for rnd in range(3):
            keys = [k for k in still if k not in fixed]
            if not keys:
                break
            chunks = [keys[i:i + CHUNK] for i in range(0, len(keys), CHUNK)]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                list(ex.map(do, chunks))
            print("  round %d: %d of %d shortened"
                  % (rnd + 1, len(fixed), len(todo)))

    # anything the rules or the model produced still has to fit the panel width
    for j, s in list(fixed.items()):
        if any(disp_cols(p) > OBJ_COLS for p in s.split("\n")):
            w = wrap_cols(s, budget[j])
            if w:
                fixed[j] = w
            else:
                del fixed[j]

    left = [k for k in todo if k not in fixed]
    print("\nshortened %d, still too long %d" % (len(fixed), len(left)))
    for j in list(fixed)[:12]:
        print("   %-52r -> %r (%d bytes, budget %d)"
              % (en[j][:50], fixed[j], enc_len(fixed[j]), budget[j]))
    for j in left:
        print("   STILL LONG budget %d (need %d): %r"
              % (budget[j], enc_len(en[j]), en[j]))

    # `wrapped` edits `en` in place, so the write must not be gated on `fixed`
    if write and (fixed or wrapped):
        en.update(fixed)
        json.dump(en, io.open(os.path.join(WORK, "analysis",
                                           "objectives_en.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote objectives_en.json (%d wrapped, %d shortened)"
              % (wrapped, len(fixed)))
    elif fixed or wrapped:
        print("(report only; pass --write to apply)")


if __name__ == "__main__":
    main()
