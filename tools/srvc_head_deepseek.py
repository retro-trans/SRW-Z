# -*- coding: utf-8 -*-
"""Translate the 108 head-truncated battle quotes.

Each ends with 」 but has no opening 「, and most carry a stray byte where a
multi-byte character was cut ('ﾌカタキだっ！」' = 'カタキだっ！」' plus debris).
That damage is in the ORIGINAL file, so translate the READABLE remainder; the
stray lead byte is dropped rather than reproduced.

Output is written wrapped in ASCII double quotes like every other battle line,
which reads better in the box than a fragment that starts mid-word.

Resumable: analysis/srvc_head_en.json, keyed by worklist index.
"""
import collections
import io
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call, parse_obj, sanitize

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 20
WORKERS = 6
MAXCOL, MAXLINES = 48, 3

# halfwidth katakana / stray ASCII at the head is cut-off debris, not text
DEBRIS = re.compile(u"^[\uFF61-\uFF9F A-Za-z\u3000\u0040\u005B\u3001\u30FB]+")

SYSTEM = (
    "You translate battle voice lines from the PS2 game Super Robot Wars Z "
    "into English. Each line here is the TAIL of a longer quote - it begins "
    "mid-sentence. Translate the fragment as it stands; do not invent the "
    "missing beginning.\n"
    "Rules:\n"
    "- Punchy spoken combat English.\n"
    "- Keep character and attack names consistent with standard English "
    "releases; romanise unknown names in Hepburn without macrons.\n"
    "- A line break is the two characters backslash-n; at most 3 lines, "
    "48 characters per line.\n"
    "- ASCII only. No Japanese characters, no em dashes. Do NOT add quote marks.\n"
    "Reply ONLY with a JSON object mapping each input line to its English."
)


def main():
    key = open(KEYFILE).read().strip()
    items = json.load(io.open(os.path.join(WORK, "analysis",
                                           "srvc_head_work.json"),
                              encoding="utf-8"))
    outp = os.path.join(WORK, "analysis", "srvc_head_en.json")
    out = {}
    if os.path.exists(outp):
        out = json.load(io.open(outp, encoding="utf-8"))

    def core(u):
        u = u.rstrip(u"　 ")
        if u.endswith(u"」"):
            u = u[:-1]
        return DEBRIS.sub("", u).strip()

    lock = threading.Lock()
    why = collections.Counter()

    def do(chunk):
        user = ("Translate each fragment.\n\n"
                + "\n".join(core(x["jp"]) for x in chunk))
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
            for x in chunk:
                v = got.get(core(x["jp"]))
                if not v:
                    why["missing"] += 1
                    continue
                v = sanitize(v).strip('"')
                if any(ord(c) > 0x7F for c in v):
                    why["non-ascii"] += 1
                    continue
                segs = v.split("\\n")
                if len(segs) > MAXLINES or any(len(s) > MAXCOL for s in segs):
                    why["too wide"] += 1
                    continue
                out[str(x["i"])] = v

    for size, label in ((CHUNK, "pass1"), (8, "retry"), (3, "retry2")):
        todo = [x for x in items if str(x["i"]) not in out and core(x["jp"])]
        if not todo:
            break
        chunks = [todo[i:i + size] for i in range(0, len(todo), size)]
        print("%s: %d lines in %d chunks" % (label, len(todo), len(chunks)))
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(out, io.open(outp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if why:
            print("   reasons: %s" % dict(why))
            why.clear()

    todo = [x for x in items if str(x["i"]) not in out and core(x["jp"])]
    print("translated %d of %d (%d missing) -> %s"
          % (len(out), len(items), len(todo), outp))


if __name__ == "__main__":
    main()
