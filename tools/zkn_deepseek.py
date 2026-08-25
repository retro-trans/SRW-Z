# -*- coding: utf-8 -*-
"""Translate encyclopedia descriptions via DeepSeek, in the batch-file format.

Same output contract as the agent batches (tools/zkn_desc_<x>.py exporting
DESC_<X> = {"PT": {id: text}, ...}), so zkn_desc_apply.py and zkn_desc_check.py
pick it up with no changes.

Usage: zkn_deepseek.py <batchname> <key> <outletter>
       e.g. zkn_deepseek.py batchK PT k

Reads analysis/zkn_work/<batch>.txt and <batch>_gloss.json, writes
tools/zkn_desc_<outletter>.py.

Entries are sent in small chunks across a thread pool. Anything that fails to
parse or comes back empty is retried once alone, then reported and SKIPPED -
a missing entry stays Japanese, which is recoverable; a silently truncated or
mis-keyed one is not.
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

WORK = r"E:\Projects\SRW Z\_work"
KEYFILE = (r"C:\Users\Binh\AppData\Local\Temp\claude\E--Projects-SRW-Z"
           r"\726977dc-ee66-4408-80d2-436333cf6c34\scratchpad\deepseek_key.txt")
MODEL = "deepseek-chat"
WORKERS = 8
CHUNK = 5            # descriptions are long; small chunks lose little on a bad parse

SANITIZE = {
    "\u2014": "-", "\u2013": "-", "\u2015": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00fc": "u", "\u00f6": "o",
    "\u00e4": "a", "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00e1": "a",
    "\u00ed": "i", "\u00f3": "o", "\u00fa": "u", "\u00f1": "n", "\u00e7": "c",
    "\u00df": "ss", "\u00c9": "E", "\u00dc": "U", "\u00d6": "O",
    "\u03b1": "Alpha", "\u03b2": "Beta", "\u03b3": "Gamma", "\u00d7": "x",
}

SYSTEM = """You translate Japanese encyclopedia entries for an English fan-translation of the PS2 game Super Robot Taisen Z.

RULES - follow exactly:
1. PARAGRAPHS ONLY, NO LINE WRAPPING. Separate paragraphs with a single \\n inside the string. NEVER insert newlines to wrap lines - a separate tool wraps to 50 columns. Each leading fullwidth space in the Japanese marks one paragraph.
2. PURE ASCII ONLY. No em/en dashes (use " - "), no curly quotes, no ellipsis character (use ...), no accented or Greek letters.
3. NAMES: use the glossary spellings given below EXACTLY, so the encyclopedia matches the game's dialogue and menus. The header line of each entry already gives official English names - reuse them verbatim. If a name is missing, transliterate it in the standard English form for that franchise. Watch vowel length (Ryouma not Ryoma, Kouji not Koji).
   If a glossary entry is obviously mangled romaji (a run-together blob like "Burakkuhoru" for what is plainly "Black Hole"), use correct English instead.
4. Japanese quotes: convert to '...' and "..." respectively.
5. These are encyclopedia entries: third person, past tense for events, present for standing traits. Keep every fact - personality, relationships, plot events, specs. Natural English prose, not word-for-word.

OUTPUT: a single JSON object mapping each id (as a string) to its translated text. No commentary, no code fences."""


def parse_obj(content):
    content = (content or "").strip()
    if not content:
        return {}
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        depth = 0
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(content[start:i + 1])
        raise


def sanitize(s):
    if not isinstance(s, str):
        s = str(s)
    for a, b in SANITIZE.items():
        s = s.replace(a, b)
    # collapse any wrapping the model added anyway: keep paragraph breaks only
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
    return "".join(ch for ch in s if ord(ch) < 128)


def call(key, system, user, tries=3):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 1.0,
        "max_tokens": 8000,
    }).encode("utf-8")
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(3 * (t + 1))
    raise last


def load_blocks(path):
    """-> [(id, header, japanese)]"""
    txt = io.open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"===(\d+)===\n(.*?)\n(.*?)(?=\n===|\Z)", txt, re.S):
        out.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return out


def main():
    batch, key_name, letter = sys.argv[1], sys.argv[2], sys.argv[3]
    api = open(KEYFILE).read().strip()
    wd = os.path.join(WORK, "analysis", "zkn_work")
    blocks = load_blocks(os.path.join(wd, batch + ".txt"))
    gloss = json.load(io.open(os.path.join(wd, batch + "_gloss.json"),
                              encoding="utf-8"))
    gtxt = "\n".join("%s = %s" % (k, v) for k, v in gloss.items())
    system = SYSTEM + "\n\nGLOSSARY (Japanese = English):\n" + gtxt
    print("%s: %d entries, %d glossary names" % (batch, len(blocks), len(gloss)))

    chunks = [blocks[i:i + CHUNK] for i in range(0, len(blocks), CHUNK)]

    def do(ch):
        user = "\n\n".join("===%s===\n%s\n%s" % b for b in ch)
        try:
            r = parse_obj(call(api, system, user))
            # A single-entry chunk sometimes comes back as a bare string
            # instead of {id: text}; adopt it rather than crashing.
            if isinstance(r, str):
                r = {ch[0][0]: r} if len(ch) == 1 else {"__error__": "bare string"}
            if not isinstance(r, dict):
                return {"__error__": "unexpected %s" % type(r).__name__}
            return r
        except Exception as e:
            return {"__error__": "%s: %s" % (type(e).__name__, e)}

    got = {}
    errs = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for ch, res in zip(chunks, ex.map(do, chunks)):
            if "__error__" in res:
                errs.append((ch, res["__error__"]))
                continue
            for rid, txt in res.items():
                got[str(rid)] = sanitize(txt)

    # retry anything missing, one entry at a time
    missing = [b for b in blocks if b[0] not in got or not got[b[0]].strip()]
    if missing:
        print("retrying %d missing entr(ies) individually..." % len(missing))
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for b, res in zip(missing, ex.map(lambda x: do([x]), missing)):
                if "__error__" not in res:
                    for rid, txt in res.items():
                        got[str(rid)] = sanitize(txt)

    valid = {}
    ids = {b[0] for b in blocks}
    for rid, txt in got.items():
        if rid in ids and txt.strip():
            valid[int(rid)] = txt.strip()
    skipped = sorted(ids - {str(k) for k in valid})
    out = os.path.join(WORK, "tools", "zkn_desc_%s.py" % letter)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write('"""Encyclopedia descriptions, batch %s (DeepSeek)."""\n'
                % letter.upper())
        f.write("DESC_%s = {\n    %r: {\n" % (letter.upper(), key_name))
        for k in sorted(valid):
            f.write("        %d: %r,\n" % (k, valid[k]))
        f.write("    },\n}\n")
    print("wrote %d/%d -> %s" % (len(valid), len(blocks), out))
    if skipped:
        print("SKIPPED (left Japanese): %s" % ", ".join(skipped))
    for ch, e in errs:
        print("  chunk error %s: %s" % ([b[0] for b in ch], e))


if __name__ == "__main__":
    main()
