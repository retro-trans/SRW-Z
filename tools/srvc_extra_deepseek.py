# -*- coding: utf-8 -*-
"""SUPERSEDED - DO NOT WIRE analysis/srvc_extra_en.json INTO THE BUILD.

Written on the belief that 581 quotes were outside srvc_work.py's enumeration.
They are not: srvc_work stores keys with the 「」 wrapper STRIPPED by inner(),
and the comparison that produced "0 in worklist" compared bracketed strings
against bracket-less keys. 519 of the 581 were in the worklist all along, and
500 are already translated in srvc_en.json.

Worse, this tool bounds every line to its original NUL slot - but all 1,202
slots sit in PARSED blocks, which srvc.build() re-lays out with recomputed
offsets, so length is free there. That false constraint is what rejected 261
lines as "too long". Use the normal srvc_work -> srvc_deepseek -> srvc_apply
path instead.

Kept only for the 62 fragments that genuinely are outside the worklist.

Original description follows.

Translate battle quotes that srvc_work.py's enumeration never reached.

srvc_work builds its list through srvc.parse(); 581 unique quotes sit in parts of
SRVC.BIN that walk never covers, so they were invisible to the whole pipeline and
still ship Japanese.

Because they are outside the parsed blocks, srvc.build() will NOT re-lay them
out - they must be written IN PLACE, so each is bound to its original NUL slot
budget. Anything that cannot be said within the budget is reported, never
truncated.

Resumable: analysis/srvc_extra_en.json is rewritten after each pass.
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
CHUNK = 20
WORKERS = 6

SYSTEM = (
    "You translate battle voice lines from the PS2 game Super Robot Wars Z "
    "into English. Series include Gundam SEED/Zeta/X/Turn A, Getter Robo, "
    "Mazinger, Zambot 3, Daitarn 3, Aquarion, Eureka Seven, King Gainer, "
    "Big O, Orguss, Xabungle, Gravion, Godsigma, Danguard Ace, Baldios, "
    "Combattler, Voltes.\n"
    "Rules:\n"
    "- These are shouted combat lines: keep them punchy and natural.\n"
    "- Japanese quote marks are the game's own; output plain ASCII double "
    "quotes around the line, matching the input's quoting.\n"
    "- Keep attack and character names consistent with standard English "
    "releases; romanise unknown names in Hepburn without macrons.\n"
    "- A line break is the two characters backslash-n. Preserve at most the "
    "same number of breaks as the input.\n"
    "- STRICT: each entry has a byte budget given as 'max N'. ASCII only, "
    "no Japanese characters, no em dashes.\n"
    "Reply ONLY with a JSON object mapping each Japanese line to its English."
)


def main():
    key = open(KEYFILE).read().strip()
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_todo.json"),
                              encoding="utf-8"))
    by_jp = collections.OrderedDict()
    for x in items:
        by_jp.setdefault(x["jp"], []).append(x)
    uniq = [{"jp": jp, "budget": min(y["budget"] for y in s), "n": len(s)}
            for jp, s in by_jp.items()]
    uniq.sort(key=lambda u: -u["n"])
    print("slots %d -> unique %d" % (len(items), len(uniq)))

    outp = os.path.join(WORK, "analysis", "srvc_extra_en.json")
    out = {}
    if os.path.exists(outp):
        out = json.load(io.open(outp, encoding="utf-8"))
        print("resuming with %d done" % len(out))

    lock = threading.Lock()
    why = collections.Counter()

    def do(chunk):
        user = ("Translate each battle line. One per line, "
                "JAPANESE<TAB>max BYTES.\n"
                "Reply with a JSON object keyed by the exact Japanese line.\n\n"
                + "\n".join("%s\tmax %d" % (u["jp"], u["budget"]) for u in chunk))
        try:
            content = call(key, SYSTEM, user)
        except Exception:
            with lock:
                why["api"] += 1
            return
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

    for size, label in ((CHUNK, "pass1"), (8, "retry"), (3, "retry2")):
        todo = [u for u in uniq if u["jp"] not in out]
        if not todo:
            break
        chunks = [todo[i:i + size] for i in range(0, len(todo), size)]
        print("%s: %d lines in %d chunks" % (label, len(todo), len(chunks)))
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
