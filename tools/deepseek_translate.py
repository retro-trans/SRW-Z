# -*- coding: utf-8 -*-
"""Translate a stage record via DeepSeek-V3, output in the same recNNN_en.py format.

Usage: deepseek_translate.py <N>
Reads key from scratchpad/deepseek_key.txt. Chunks rows, sends a cached system
prompt (rules + record-relevant glossary), parses JSON back, writes recNNN_en.py,
then runs a cp932 budget check. Overflows are left for tighten_record.py.
"""
import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

WORK = r'E:\Projects\SRW Z\_work'
WORKERS = 12
KEYFILE = (r'C:\Users\Binh\AppData\Local\Temp\claude\E--Projects-SRW-Z'
           r'\726977dc-ee66-4408-80d2-436333cf6c34\scratchpad\deepseek_key.txt')
KEY = open(KEYFILE).read().strip()
CHUNK = 18  # thinking disabled -> small output; smaller chunks lose fewer rows per bad parse


SANITIZE = {
    '—': '-', '–': '-', '―': '-', '‘': "'", '’': "'",
    '“': '"', '”': '"', '…': '..', 'ü': 'u', 'ö': 'o',
    'ä': 'a', 'é': 'e', 'è': 'e', 'ê': 'e', 'á': 'a',
    'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ç': 'c',
    'ß': 'ss', 'É': 'E', 'Ü': 'U', 'Ö': 'O',
}


def coerce(v):
    """DeepSeek sometimes returns the value as a dict/list instead of a string."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        # prefer keys that look like a translation, else first string value
        for key in ("english", "translation", "en", "text", "value"):
            if key in v and isinstance(v[key], str):
                return v[key]
        for x in v.values():
            if isinstance(x, str):
                return x
        return ""
    if isinstance(v, list):
        return " ".join(coerce(x) for x in v)
    return str(v)


def parse_obj(content):
    """Robustly parse a JSON object out of a model response (may have fences/trailing)."""
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
        # extract the first balanced {...}
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
    s = coerce(s)
    for a, b in SANITIZE.items():
        s = s.replace(a, b)
    # drop any remaining non-cp932 chars
    out = []
    for ch in s:
        try:
            ch.encode('cp932')
            out.append(ch)
        except UnicodeEncodeError:
            pass
    return "".join(out)


def bl(s):
    return len(s.encode('cp932', 'replace'))


def call(system, user):
    body = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
    }).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=body,
                                 headers={"Authorization": "Bearer " + KEY,
                                          "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            r = urllib.request.urlopen(req, timeout=180)
            d = json.load(r)
            return d["choices"][0]["message"]["content"], d.get("usage", {})
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError("HTTP %d: %s" % (e.code, e.read().decode()[:300]))
    raise RuntimeError("retries exhausted")


def main():
    n = int(sys.argv[1])
    rows = json.load(open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))
    gloss = json.load(open(WORK + r'\analysis\glossary.json', encoding='utf-8'))
    alltext = "".join(r['jp'] for r in rows)
    rel = {jp: en for jp, en in gloss.items() if jp in alltext}
    gloss_lines = "\n".join("%s = %s" % (jp, en) for jp, en in rel.items())

    system = (
        "You are an expert JP->EN translator for a fan-translation of the PS2 game "
        "Super Robot Taisen Z, a crossover of ~20 mecha anime. Translate dialogue "
        "idiomatically and in-character.\n\n"
        "RULES (critical):\n"
        "- Input is a JSON object mapping row-id -> Japanese text. Output a JSON "
        "object mapping the SAME ids -> English. Translate EVERY id; add none, drop none.\n"
        "- Each line begins with a speaker name then a newline then the quote, e.g. "
        "'Name\\n\"quote\"'. KEEP the speaker name + newline. Keep internal newlines "
        "roughly matching the Japanese line count (the game text box wraps on them).\n"
        "- Convert Japanese quotes to straight ASCII: convert corner brackets to "
        "double-quotes, and full-width parentheses to normal parentheses.\n"
        "- Preserve the placeholders $n $F $f $c EXACTLY as-is (they are runtime "
        "substitutions). Never translate or alter them.\n"
        "- Scene-header rows look like full-width spaces then a wave-dash Location "
        "wave-dash. Keep that exact full-width formatting; translate ONLY the location.\n"
        "- KEEP IT CONCISE: the game has tight text limits, so aim for short, natural "
        "phrasing (English runs long). Prefer contractions.\n"
        "- Output must be encodable in cp932 (Japanese Shift-JIS). Use plain ASCII "
        "punctuation only: no em-dashes, no smart/curly quotes, no ellipsis char "
        "(use '..').\n\n"
        "GLOSSARY (use these exact spellings for any name that appears):\n" + gloss_lines
    )

    # hard cap on API calls for this record so retries can never run away
    max_calls = len(range(0, len(rows), CHUNK)) * 2 + 20
    calls = [0]

    def do_call(chunk_rows):
        if calls[0] >= max_calls:
            return {}, 0
        calls[0] += 1
        payload = {str(r['i']): {"jp": r['jp'], "max_chars": r['budget']} for r in chunk_rows}
        user = ("Translate each row's `jp` to English. Every translation MUST fit "
                "within its `max_chars` limit (count ALL characters including the "
                "speaker name, newlines, and spaces; ASCII chars are 1 each). Going "
                "under the limit is good. Return ONLY a JSON object mapping EVERY id "
                "(as a string key) to its English translation - include all ids.\n\n"
                + json.dumps(payload, ensure_ascii=False))
        # catch EVERYTHING (HTTP errors, timeouts, parse) so one bad call can never
        # abort the whole ThreadPoolExecutor.map loop and strand the remaining chunks
        try:
            content, usage = call(system, user)
            return parse_obj(content), usage.get("total_tokens", 0)
        except Exception as e:
            print("    call/parse fail: %s" % str(e)[:60])
            return {}, 0

    T = {}
    usage_tot = [0]

    def absorb(obj, tok):
        usage_tot[0] += tok
        for k, v in obj.items():
            try:
                T[int(k)] = sanitize(v)
            except (ValueError, TypeError):
                pass

    chunks = [rows[c:c + CHUNK] for c in range(0, len(rows), CHUNK)]
    t0 = time.time()
    print("  %d chunks, %d workers..." % (len(chunks), WORKERS), flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        # translate all chunks concurrently
        done = 0
        for obj, tok in ex.map(do_call, chunks):
            absorb(obj, tok)
            done += 1
            if done % 10 == 0:
                print("    %d/%d chunks, %d rows, %.0fs" % (done, len(chunks), len(T), time.time() - t0), flush=True)
        print("  main pass: %d/%d rows in %.0fs" % (len(T), len(rows), time.time() - t0), flush=True)
        # parallel completeness sweeps for any missing rows (call-budget bounded)
        for sweep in range(6):
            miss = [r for r in rows if r['i'] not in T]
            if not miss or calls[0] >= max_calls:
                break
            print("  sweep %d: %d missing" % (sweep + 1, len(miss)))
            mchunks = [miss[c:c + 12] for c in range(0, len(miss), 12)]
            for obj, tok in ex.map(do_call, mchunks):
                absorb(obj, tok)
    usage_tot = usage_tot[0]
    still = len([r for r in rows if r['i'] not in T])
    print("  %d/%d rows (%d unfilled, %d calls, %d tok)"
          % (len(rows) - still, len(rows), still, calls[0], usage_tot))

    # drop any stray ids the model invented (not in the source)
    valid_ids = {r['i'] for r in rows}
    for k in [k for k in T if k not in valid_ids]:
        del T[k]

    # write file
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue (DeepSeek)."""' % n,
             "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec%03d_en.py" % n, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    # verify
    wk = {r['i']: r for r in rows}
    need = set(wk)
    got = set(T)
    over = [(i, bl(T[i]), wk[i]['budget']) for i in T if i in wk and bl(T[i]) > wk[i]['budget']]
    print("rec%03d: %d/%d rows | missing %s | extra %s | over %d | %d tokens total"
          % (n, len(T), len(need), sorted(need - got)[:10], sorted(got - need)[:10],
             len(over), usage_tot))


if __name__ == "__main__":
    main()
