# -*- coding: utf-8 -*-
"""Translate the leftover Japanese stage rows via DeepSeek.

Input  analysis/missing2_todo.json  {jp: [[rec,row,off,budget], ...]}
Output analysis/missing2_en.json    {jp: english}

These are the rows the original script sweep missed: short reactions
("$n\\n「え…？」"), faction/unit names embedded in text, and some long library
entries. 238 of the 1,724 were already resolvable from name_source.json and are
handled separately - only the rest come here.

TWO THINGS MAKE THIS DIFFERENT FROM THE ENCYCLOPEDIA PASS:
  * BUDGETS. These are fixed slots in the stage record, not resizable chunks, so
    every translation must fit its byte budget or apply_stage silently leaves the
    row Japanese. The budget is passed to the model per line and re-checked here.
  * LEADING CONTROL BYTES. A leading 0x0C/0x01/0x04/0x0D marks a glossary-link
    keyword. It is stripped before translating and re-prepended on apply, so the
    model never sees or invents one.
"""
import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call, parse_obj, sanitize

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 20
WORKERS = 8

SYSTEM = """You translate Japanese text from the PS2 game Super Robot Taisen Z into English for a fan translation.

The input is one item per line, formatted:
<id>\t<budget>\t<Japanese>

RULES:
1. HARD LENGTH LIMIT. Your English for each item must be AT MOST <budget> characters, counting every character including spaces and newlines. This is a fixed slot in the game; longer text is discarded and the line stays Japanese. Shorter is always fine. Abbreviate rather than overrun.
2. PURE ASCII ONLY. No em/en dashes (use -), no curly quotes, no ellipsis character (use ... or just .), no accented letters.
3. KEEP THE LINE STRUCTURE. If the Japanese contains \\n, keep the same number of \\n in your output. A line like "$n\\n「え…？」" is a speaker name then their quote: translate it as "$n\\n\"Huh...?\"" - keep $n, $c, $F, $f placeholders EXACTLY as they are, they are runtime name substitutions.
4. Japanese quote marks: 「...」 -> "..."  and 『...』 -> '...'
5. Many items are just a NAME (a faction, ship, unit or term). Use the standard English name for that franchise - these are Gundam / Mazinger / Getter / Xabungle / Turn A / Orguss / Baldios / Big O / Eureka Seven / Aquarion / Gravion / King Gainer / Zambot / Daitarn / God Sigma titles. Never transliterate a Western word mora by mora (ブラックホール is "Black Hole", NOT "Burakkuhoru").
6. Natural spoken English for dialogue; keep the speaker's register.

OUTPUT: a single JSON object mapping each <id> (as a string) to the translated text. No commentary, no code fences."""


def main():
    a = os.path.join(WORK, "analysis")
    todo = json.load(io.open(os.path.join(a, "missing2_todo.json"), encoding="utf-8"))
    api = open(KEYFILE).read().strip()
    items = []
    for jp, locs in todo.items():
        i = 0
        while i < len(jp) and ord(jp[i]) < 0x20 and jp[i] != "\n":
            i += 1
        body = jp[i:]
        bud = min(x[3] for x in locs) - i          # control bytes cost budget too
        if bud < 2 or not body.strip():
            continue
        items.append((len(items), jp, body, bud))
    print("items to translate: %d" % len(items))
    chunks = [items[i:i + CHUNK] for i in range(0, len(items), CHUNK)]

    def do(ch):
        lines = []
        for idx, jp, body, bud in ch:
            lines.append("%d\t%d\t%s" % (idx, bud, body.replace("\n", "\\n")))
        try:
            r = parse_obj(call(api, SYSTEM, "\n".join(lines)))
            return r if isinstance(r, dict) else {}
        except Exception:
            return {}

    got = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(do, chunks):
            got.update(res)

    out = {}
    over = miss = 0
    for idx, jp, body, bud in items:
        v = got.get(str(idx))
        if not isinstance(v, str) or not v.strip():
            miss += 1
            continue
        v = sanitize(v.replace("\\n", "\n")).strip("\n")
        if len(v.encode("cp932", "replace")) > bud:
            over += 1
            continue
        out[jp] = v
    p = os.path.join(a, "missing2_en.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("translated %d, over budget %d, no answer %d -> %s"
          % (len(out), over, miss, p))


if __name__ == "__main__":
    main()
