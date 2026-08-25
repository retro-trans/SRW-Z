# -*- coding: utf-8 -*-
"""Translate the encyclopedia's remaining NAME fields via DeepSeek.

Names are the highest-risk text in this project: a wrong description reads
oddly, a wrong name contradicts the dialogue and the unit list. The prompt
therefore carries the project's actual failure mode - the kata_romaji fallback
that produced "Jakkukaba" for ジャック・カーバー (Jack Carver) - as an explicit
prohibition, and every name is sent WITH its series so the model can reach for
the franchise's established English spelling instead of transliterating.

Reads analysis/zkn_names_todo.json ({field: {jp: [series, related]}}).
Writes analysis/zkn_names_new.json ({jp: english}).

Usage: zkn_names_deepseek.py [field ...]      (default: all fields)
"""
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zkn_deepseek import KEYFILE, call, parse_obj, sanitize

WORK = r"E:\Projects\SRW Z\_work"
CHUNK = 25
WORKERS = 8

BASE = """You romanise Japanese names for an English fan-translation of the PS2 game Super Robot Taisen Z. It adapts these anime: Mazinger Z, Great Mazinger, UFO Robo Grendizer, Getter Robo G, Combat Mecha Xabungle, Space Warrior Baldios, Space Emperor God Sigma, Invincible Superman Zambot 3, Invincible Steel Man Daitarn 3, Super Dimension Century Orguss, Mobile Suit Z Gundam, Char's Counterattack, After War Gundam X, Turn A Gundam, Mobile Suit Gundam SEED DESTINY, Overman King Gainer, The Big O, Eureka Seven, Genesis of Aquarion, Gravion, and Banpresto originals.

ABSOLUTE RULE - this is the mistake to avoid:
NEVER output a mora-by-mora transliteration of a name that is really a Western word.
  WRONG: ジャック・カーバー -> "Jakkukaba"      RIGHT: "Jack Carver"
  WRONG: ブラックホール   -> "Burakkuhoru"     RIGHT: "Black Hole"
  WRONG: タンホイザー     -> "Tanhoiza"        RIGHT: "Tannhauser"
The middle dot (・) separates words - keep them as separate English words.

RULES:
1. Use the OFFICIAL/most widely used English spelling for that franchise. The series is given for every name - use it.
2. Japanese personal names: Hepburn, GIVEN NAME FIRST then surname (兜甲児 -> "Kouji Kabuto"). Keep long vowels as the glossary does (Kouji, Ryouma, Touga).
3. PURE ASCII only. No accents, no macrons, no Greek letters.
4. If a name is a rank, title or placeholder rather than a name (e.g. 大尉, －－－, ？？？), translate it sensibly ("Captain", "---", "???").
5. Keep it SHORT - these go in narrow UI fields. No epithets, no parentheses, no extra description.

OUTPUT: a single JSON object mapping each Japanese name EXACTLY as given to its English form. No commentary, no code fences."""

FIELD_NOTE = {
    "RT/RBTN": "These are ROBOT / mobile suit / mecha names.",
    "RT/PLTN": "These are PILOT names (people).",
    "PT/CHFN": "These are CHARACTERS' FULL names. The related short name is given as a hint.",
    "PT/CHNN": "These are CHARACTERS' SHORT names (given name or nickname). The full name is given as a hint.",
    "PT/ACTR": ("These are the names of REAL JAPANESE VOICE ACTORS. Romanise the actual "
                "person's name in standard Hepburn, given name first (e.g. 石丸博也 -> "
                "'Hiroya Ishimaru'). If unsure of the reading, give the most common one."),
}


def main():
    a = os.path.join(WORK, "analysis")
    todo = json.load(io.open(os.path.join(a, "zkn_names_todo.json"), encoding="utf-8"))
    gloss = json.load(io.open(os.path.join(a, "name_source.json"), encoding="utf-8"))
    api = open(KEYFILE).read().strip()
    fields = sys.argv[1:] or list(todo)
    out = {}
    for field in fields:
        items = sorted(todo[field].items())
        if not items:
            continue
        # only glossary entries relevant to this field's series, capped
        gsub = {k: v for k, v in list(gloss.items())[:900]}
        system = (BASE + "\n\n" + FIELD_NOTE.get(field, "") +
                  "\n\nEXISTING SPELLINGS already used in this patch (match them):\n" +
                  "\n".join("%s = %s" % (k, v) for k, v in list(gsub.items())[:600]))
        chunks = [items[i:i + CHUNK] for i in range(0, len(items), CHUNK)]

        def do(ch):
            lines = []
            for name, (series, extra) in ch:
                s = "%s   [series: %s]" % (name, series or "?")
                if extra:
                    s += "   [related name: %s]" % extra
                lines.append(s)
            try:
                r = parse_obj(call(api, system, "\n".join(lines)))
                return r if isinstance(r, dict) else {}
            except Exception:
                return {}

        got = {}
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for res in ex.map(do, chunks):
                got.update(res)
        n = 0
        for name, _ in items:
            v = got.get(name)
            if isinstance(v, str) and v.strip():
                out[name] = sanitize(v).strip()
                n += 1
        print("  %-10s %3d/%3d translated" % (field, n, len(items)))
    p = os.path.join(a, "zkn_names_new.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %d names -> %s" % (len(out), p))


if __name__ == "__main__":
    main()
