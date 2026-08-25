# -*- coding: utf-8 -*-
"""Shorten battle quotes so none EXCEEDS its original byte length.

WHY THIS IS MANDATORY (found by tracing the game, 2026-08-17):

  002EA644  lw   v1, 4(s0)        ; per-line record: u32 offset into the pool
            lw   a0, 0x248(a0)    ; string-pool base
            addu s0, a0, v1       ; source = pool_base + offset

The game locates each quote by a stored BYTE OFFSET. Those per-line records sit
in the part of the block that srvc.parse lumps into `b.head`, and srvc.build()
re-emits the head VERBATIM - so the offsets keep their ORIGINAL values. (parse
detects only ONE trailing index entry per block, though a block holds hundreds
of strings, which is why this went unnoticed: a round-trip of the untouched file
is byte-identical.)

Consequence: the instant one string changes length, every string after it in
that block sits at the wrong offset and the game reads from the MIDDLE of it -
which is the "missing head" seen in game, varying per line and unrelated to the
speaker or to timing.

Keeping every string EXACTLY its original byte length keeps the pool layout
byte-identical, so every stored offset stays valid. srvc_apply pads short
strings up to the original length; this tool shortens the ones that are too
long, which is the other half of the same rule.

Usage: srvc_bytefit.py [rounds]
"""
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc
from srvc_work import inner, is_quote, load_blocks
from patch import encode as pencode
from zkn_deepseek import KEYFILE, call
from srvc_deepseek import norm, parse_map, load_gloss, chunk_gloss
from srvc_refit import budgets, fits

# The battle box is drawn by the MENU reader (0x13A290), where bytes 0x2E-0x3D
# (. / 0-9 : ; < =) are CONTROL CODES that also swallow a parameter byte - which
# is why '"..."' rendered as a single quote mark and why every line lost
# everything from its first full stop onward. They must go in MENU-ENCODED, as
# fullwidth forms, so each one costs TWO bytes and TWO display columns.
MODE = "menu"


def enc_len(v):
    return len(pencode('"' + v + '"', MODE))


def disp_cols(v):
    """Widest row in display columns (fullwidth punctuation counts double)."""
    return max(sum(2 if 0x2E <= ord(c) <= 0x3D else 1 for c in row)
               for row in v.split("\\n"))

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 10
WORKERS = 8

SYSTEM = """You shorten BATTLE VOICE lines for an English fan-translation of the PS2 game Super Robot Taisen Z - the short shouts a pilot makes during an attack.

Each line comes with a MAX byte count. This is a hard limit: the game stores these strings at fixed byte offsets, and a line that exceeds its budget corrupts the text that follows it.

RULES - follow exactly:
1. Stay within the MAX bytes. Letters, spaces and , ! ? ' - cost ONE byte each. But a FULL STOP and every DIGIT cost TWO bytes each, because the game needs them in a wide form. So "..." costs 6 bytes, not 3, and "3 turns." costs 10. Prefer to end a line with ! or nothing rather than spend 2 bytes on a full stop, and avoid "..." unless the pause really matters.
2. PURE ASCII, and only these characters: letters, digits, space, and . , ! ? ' " -
3. Do NOT add surrounding quote marks - the game draws those itself.
4. At most 2 rows, separated by a literal backslash followed by n, each row at most 32 characters.
5. These are shouted in combat: punchy and idiomatic. Keep the exclamation marks. Preserve the meaning, but cut hard - drop adjectives, use shorter synonyms, compress. A terse shout is much better than one that does not fit.
6. Use the glossary spellings exactly for names and attacks.

OUTPUT: a single JSON object mapping each id (as a string) to the shortened line. No commentary, no code fences."""


def orig_budgets():
    """jp text -> smallest original byte length across all its slots."""
    data, seg, blocks = load_blocks()
    m = {}
    for b in blocks:
        if not b.has_text:
            continue
        for s in b.strings:
            if not is_quote(s):
                continue
            k = inner(s.decode("cp932"))
            n = len(s)
            if k not in m or n < m[k]:
                m[k] = n
    return m


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    items = json.load(io.open(os.path.join(WORK, "analysis",
                                           "srvc_work.json"), encoding="utf-8"))
    p = os.path.join(WORK, "analysis", "srvc_en.json")
    en = json.load(io.open(p, encoding="utf-8"))
    by = {str(x["i"]): x for x in items}
    ob = orig_budgets()

    def over():
        out = []
        for k, v in en.items():
            b = ob.get(by[k]["jp"])
            if b is None:
                continue
            if enc_len(v) > b:
                out.append(k)
        return out

    todo = over()
    print("%s of %s lines exceed their original byte length"
          % ("{:,}".format(len(todo)), "{:,}".format(len(en))))
    if not todo:
        return

    gloss = load_gloss()
    api = open(KEYFILE).read().strip()
    lock = threading.Lock()

    for rnd in range(rounds):
        todo = over()
        if not todo:
            break
        print("round %d: %s to shorten" % (rnd + 1, "{:,}".format(len(todo))))
        chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
        fixed = [0]
        done = [0]

        def do(ch):
            g = chunk_gloss(gloss, [by[k]["jp"] for k in ch])
            user = ""
            if g:
                user += ("GLOSSARY (use these spellings exactly):\n" +
                         "\n".join(g) + "\n\n")
            user += "Shorten each line. id<TAB>MAXBYTES<TAB>japanese<TAB>current english\n"
            for k in ch:
                b = ob[by[k]["jp"]] - 2          # our two quote marks
                user += "%s\t%d\t%s\t%s\n" % (k, b, by[k]["jp"], en[k])
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
                if not v:
                    continue
                if enc_len(v) > ob[by[k]["jp"]]:
                    continue
                if disp_cols(v) > 32 or len(v.split("\\n")) > 2:
                    continue
                got[k] = v
            with lock:
                en.update(got)
                fixed[0] += len(got)
                done[0] += 1
                if done[0] % 25 == 0 or done[0] == len(chunks):
                    json.dump(en, io.open(p, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=1)
                    print("   %d/%d chunks | shortened %s"
                          % (done[0], len(chunks), "{:,}".format(fixed[0])))

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(do, chunks))
        json.dump(en, io.open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if not fixed[0]:
            break

    left = over()
    print("done: %s still too long" % "{:,}".format(len(left)))
    for k in left[:10]:
        print("   budget %d, have %d: %r"
              % (ob[by[k]["jp"]], enc_len(en[k]), en[k]))


if __name__ == "__main__":
    main()
