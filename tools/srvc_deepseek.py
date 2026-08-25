# -*- coding: utf-8 -*-
"""Translate the battle voice lines (BTL/SRVC.BIN) via DeepSeek.

Unlike the stage records and COMPDATA, SRVC strings are NOT byte-budgeted:
srvc.build() recomputes every index offset and re-emits SRVC.SEG, and a
parse->build round-trip is byte-identical, so a line may be any length. The
real constraint is the on-screen box, measured from the Japanese: the longest
segment between line breaks is 24 fullwidth chars = 48 half-width columns, and
no line uses more than 2 breaks (3 display lines).

The break marker in this file is a LITERAL backslash-n, not 0x0A.

Each chunk carries only the glossary entries that actually occur in its lines,
so attack names agree with weapons_en.json and character names with
name_source.json without paying for a 2,900-entry glossary on every request.

Resumable: analysis/srvc_en.json is rewritten after every completed chunk, and
a re-run skips whatever is already in it.

Usage: srvc_deepseek.py [limit]      # limit = translate only the first N lines
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
CHUNK = 25
WORKERS = 8
MAXCOL = 48          # half-width columns per display line
MAXLINES = 3
GLOSS_PER_CHUNK = 40

SYSTEM = """You translate BATTLE VOICE lines for an English fan-translation of the PS2 game Super Robot Taisen Z. These are the short shouts a pilot makes while attacking, being hit, dodging, or being defeated - they appear in a small box during the battle animation.

RULES - follow exactly:
1. PURE ASCII ONLY. No em/en dashes (use -), no curly quotes, no ellipsis character (use ...), no accented letters, no Japanese characters.
2. Do NOT add surrounding quote marks - the game draws those itself. Output the bare line.
3. LINE BREAKS: the marker is a literal backslash followed by n. Keep each display line at most 48 characters. Use at most 2 breaks (3 display lines). If the Japanese has a break, you do not have to put yours in the same place - break wherever the English reads best, or drop it if the English fits on one line.
4. NAMES AND ATTACKS: use the glossary spellings given below EXACTLY. Attack/weapon names must match the glossary so the battle box agrees with the weapon menu. If a name is not in the glossary, transliterate it in the standard English form for that franchise.
5. REGISTER: these are shouted in combat. Keep them punchy and idiomatic - short exclamations, not literal prose. Match the speaker's tone: arrogant villains sneer, hot-blooded heroes yell, calm veterans stay terse. Keep the exclamation marks the Japanese uses.
6. Do not translate the line into a description of it. Give the actual words spoken.

OUTPUT: a single JSON object mapping each id (as a string) to its translated line. No commentary, no code fences."""


def load_gloss():
    g = {}
    for f in ("name_source.json", "weapons_en.json", "glossary.json"):
        p = os.path.join(WORK, "analysis", f)
        if os.path.exists(p):
            for k, v in json.load(io.open(p, encoding="utf-8")).items():
                if len(k) >= 2 and isinstance(v, str) and v.strip():
                    g.setdefault(k, v)
    return sorted(g.items(), key=lambda kv: -len(kv[0]))


def chunk_gloss(gloss, lines):
    joined = "\n".join(lines)
    hits = []
    for k, v in gloss:
        if k in joined:
            hits.append("%s = %s" % (k, v))
            if len(hits) >= GLOSS_PER_CHUNK:
                break
    return hits


PAIR = re.compile(r'"(\d+)"\s*:\s*"((?:[^"\\]|\\.)*)"')


def parse_map(content):
    """Tolerant id->text extraction.

    parse_obj handles fenced JSON, but this model sometimes drops the enclosing
    braces and emits a bare run of `"0": "...",` pairs. json.loads then reads
    the first string and reports Extra data, and parse_obj's brace-matching
    fallback has no `{` to anchor on, so it re-raises and the whole chunk is
    lost. Try the strict parse, then a braced retry, then scrape the pairs -
    which also salvages a response that was truncated mid-object.
    """
    try:
        r = parse_obj(content)
        if isinstance(r, dict) and r:
            return r
    except Exception:
        pass
    body = (content or "").strip()
    if body.startswith("```"):
        body = body.split("```", 2)[1]
        if body.startswith("json"):
            body = body[4:]
        body = body.strip().rstrip("`").strip()
    try:
        r = json.loads("{" + body.strip().strip(",") + "}")
        if isinstance(r, dict):
            return r
    except Exception:
        pass
    out = {}
    for k, v in PAIR.findall(body):
        try:
            out[k] = json.loads('"' + v + '"')
        except Exception:
            continue
    return out


def norm(v):
    """Model output -> the game's own break convention.

    A JSON "\\n" decodes to a REAL newline, but this file breaks lines with a
    LITERAL backslash-n, so every real newline has to be converted back or the
    line arrives as one long unbroken string.
    """
    v = sanitize(v)
    v = v.replace("\r\n", "\n").replace("\r", "\n")
    v = re.sub(r"\s*\n\s*", "\\\\n", v)          # real newline -> \n marker
    v = re.sub(r"\s*\\n\s*", "\\\\n", v)         # tidy spaces around markers
    return v.strip().strip('"').strip()


def bad(en):
    """Reject anything that would look wrong in the box."""
    if not en or not en.strip():
        return "empty"
    if any(ord(c) > 126 for c in en):
        return "non-ascii"
    parts = en.split("\\n")
    if len(parts) > MAXLINES:
        return "%d display lines" % len(parts)
    for p in parts:
        if len(p) > MAXCOL:
            return "line of %d cols" % len(p)
    return None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))
    if limit:
        items = items[:limit]
    outp = os.path.join(WORK, "analysis", "srvc_en.json")
    out = (json.load(io.open(outp, encoding="utf-8"))
           if os.path.exists(outp) else {})
    todo = [x for x in items if str(x["i"]) not in out]
    print("%s lines total, %s already done, %s to do"
          % ("{:,}".format(len(items)), "{:,}".format(len(out)),
             "{:,}".format(len(todo))))
    if not todo:
        return

    gloss = load_gloss()
    api = open(KEYFILE).read().strip()
    lock = threading.Lock()

    def run_pass(pending, size, label):
        """One sweep over `pending`; returns the ids still missing."""
        chunks = [pending[i:i + size] for i in range(0, len(pending), size)]
        stats = {"ok": 0, "bad": 0, "done": 0}
        why_count = collections.Counter()

        def do(ch):
            g = chunk_gloss(gloss, [x["jp"] for x in ch])
            user = ""
            if g:
                user += ("GLOSSARY (use these spellings exactly):\n" +
                         "\n".join(g) + "\n\n")
            user += "Translate each line. id<TAB>japanese\n"
            user += "\n".join("%d\t%s" % (x["i"], x["jp"]) for x in ch)
            try:
                r = parse_map(call(api, SYSTEM, user))
                if not isinstance(r, dict):
                    r, err = {}, "response was %s, not an object" % type(r).__name__
                else:
                    err = None
            except Exception as e:
                r, err = {}, "%s: %s" % (type(e).__name__, str(e)[:90])
            got = {}
            for x in ch:
                v = r.get(str(x["i"]))
                if not isinstance(v, str):
                    continue
                v = norm(v)
                w = bad(v)
                if w:
                    with lock:
                        why_count[w.split(" of ")[0]] += 1
                    continue
                got[str(x["i"])] = v
            with lock:
                if err:
                    why_count[err] += 1
                out.update(got)
                stats["ok"] += len(got)
                stats["done"] += 1
                if stats["done"] % 20 == 0 or stats["done"] == len(chunks):
                    json.dump(out, io.open(outp, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=1)
                    print("  %s %d/%d chunks | have %s"
                          % (label, stats["done"], len(chunks),
                             "{:,}".format(len(out))))

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(out, io.open(outp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if why_count:
            print("  reasons: " + ", ".join(
                "%s x%d" % (k, v) for k, v in why_count.most_common(6)))
        return [x for x in pending if str(x["i"]) not in out]

    pending = todo
    for size, label in ((CHUNK, "pass1"), (8, "retry"), (3, "retry2")):
        if not pending:
            break
        print("%s: %s lines in chunks of %d"
              % (label, "{:,}".format(len(pending)), size))
        pending = run_pass(pending, size, label)

    print("translated %s of %s (%s still missing) -> %s"
          % ("{:,}".format(len(out)), "{:,}".format(len(items)),
             "{:,}".format(len(pending)), outp))


if __name__ == "__main__":
    main()
