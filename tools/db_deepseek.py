# -*- coding: utf-8 -*-
"""Translate the remaining pilot/character DB fields in COMPDATA via DeepSeek.

Scope comes from analysis/db_todo.json (tools/scope_remaining.py), which filters
out binary that merely decodes as Shift-JIS - COMPDATA's first 0x66380 bytes are
mostly structures, and 448 of 1,112 "Japanese-looking" strings there are noise.
Feeding those to a translator and writing the result back would corrupt the
database, so only strict kana/kanji text is offered.

These are short fields (names, nicknames, unit labels) in NUL slots, so the
budget is the slot minus its terminator. Anything that does not fit is reported
rather than truncated.

Resumable: analysis/db_en.json is rewritten after each chunk.
"""
import collections
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call, parse_obj, sanitize

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 30
WORKERS = 6

SYSTEM = (
    "You translate Japanese text from the PS2 game Super Robot Wars Z into "
    "English. These are short database fields: character names, nicknames, "
    "callsigns and unit labels.\n"
    "Rules:\n"
    "- Use the official English name when the character is from a known anime "
    "(Getter Robo, Mazinger, Gundam, Zambot 3, Daitarn 3, Aquarion, Eureka "
    "Seven, King Gainer, Big O, Orguss, Xabungle, Gravion, Godsigma, Danguard "
    "Ace, Baldios, Combattler, Voltes).\n"
    "- Personal names use Hepburn romanisation without macrons (Ryouma, Kouji).\n"
    "- Nicknames and descriptive words become natural English.\n"
    "- Keep it SHORT: each entry has a strict byte budget, given as 'max N'.\n"
    "- ASCII only. No Japanese characters in the output. No em dashes.\n"
    "Reply ONLY with a JSON object mapping each id to its English string."
)


def main():
    key = open(KEYFILE).read().strip()
    items = json.load(io.open(os.path.join(WORK, "analysis", "db_todo.json"),
                              encoding="utf-8"))
    # dedupe by japanese text; one translation fills every slot that repeats it
    by_jp = collections.OrderedDict()
    for x in items:
        by_jp.setdefault(x["jp"], []).append(x)
    uniq = [{"jp": jp, "budget": min(y["budget"] for y in slots),
             "n": len(slots)} for jp, slots in by_jp.items()]
    print("slots %d -> unique %d" % (len(items), len(uniq)))

    outp = os.path.join(WORK, "analysis", "db_en.json")
    out = {}
    if os.path.exists(outp):
        out = json.load(io.open(outp, encoding="utf-8"))
        print("resuming with %d already done" % len(out))

    todo = [u for u in uniq if u["jp"] not in out]
    lock = threading.Lock()
    why = collections.Counter()

    def do(chunk):
        user = ("Translate each entry. One per line, JAPANESE<TAB>max BYTES.\n"
                "Reply with a JSON object keyed by the exact Japanese string.\n\n"
                + "\n".join("%s\tmax %d" % (u["jp"], u["budget"]) for u in chunk))
        try:
            content = call(key, SYSTEM, user)
        except Exception:
            with lock:
                why["api"] += 1
            return
        # parse_obj RAISES on non-JSON rather than returning None, and a single
        # malformed reply would otherwise kill the whole ThreadPool run
        try:
            got = parse_obj(content) or {}
        except Exception:
            with lock:
                why["bad json"] += 1
            return
        with lock:
            for u in chunk:
                v = got.get(u["jp"])
                if not v:
                    why["missing"] += 1
                    continue
                v = sanitize(v)
                if any(ord(c) > 0x7F for c in v):
                    why["non-ascii"] += 1
                    continue
                if len(v.encode("cp932", "replace")) > u["budget"]:
                    why["too long"] += 1
                    continue
                out[u["jp"]] = v

    for size, label in ((CHUNK, "pass1"), (10, "retry"), (4, "retry2")):
        todo = [u for u in uniq if u["jp"] not in out]
        if not todo:
            break
        chunks = [todo[i:i + size] for i in range(0, len(todo), size)]
        print("%s: %d entries in %d chunks" % (label, len(todo), len(chunks)))
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(out, io.open(outp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        if why:
            print("   reasons: %s" % dict(why))
            why.clear()

    todo = [u for u in uniq if u["jp"] not in out]
    print("translated %d of %d (%d missing) -> %s"
          % (len(out), len(uniq), len(todo), outp))


if __name__ == "__main__":
    main()
