# -*- coding: utf-8 -*-
"""Re-translate ONLY the over-budget rows of recNNN_en.py via DeepSeek, passing
each row's exact cp932 byte budget so the output fits. Iterates a few rounds.

Usage: deepseek_fit.py <N>
"""
import importlib.util as u
import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

WORK = r'E:\Projects\SRW Z\_work'
KEYFILE = (r'C:\Users\Binh\AppData\Local\Temp\claude\E--Projects-SRW-Z'
           r'\726977dc-ee66-4408-80d2-436333cf6c34\scratchpad\deepseek_key.txt')
KEY = open(KEYFILE).read().strip()

_ds = u.spec_from_file_location('ds', 'deepseek_translate.py')
_dm = u.module_from_spec(_ds)
_ds.loader.exec_module(_dm)
sanitize = _dm.sanitize


def bl(s):
    return len(s.encode('cp932', 'replace'))


import re
MSUBS = [
    ("  ", " "), ("...", ".."), ("!!!", "!!"),
    ("cannot", "can't"), ("Cannot", "Can't"),
    (" will ", "'ll "), (" would ", "'d "), (" is not", " isn't"),
    (" are not", " aren't"), (" do not", " don't"), (" does not", " doesn't"),
    (" did not", " didn't"), (" have not", " haven't"), (" has not", " hasn't"),
    (" I am ", " I'm "), (" you are ", " you're "), (" we are ", " we're "),
    (" they are ", " they're "), (" that is ", " that's "), (" it is ", " it's "),
    (" will not", " won't"), (" cannot ", " can't "),
    (" really ", " "), (" just ", " "), (" very ", " "), (" quite ", " "),
    (" actually ", " "), (" simply ", " "), (" even ", " "), (" only ", " "),
    (" also ", " "), (" now", ""), (" right now", ""), (" as well", ""),
    (" of course", ""), (" you know", ""), (" I mean ", " "),
    (" Federation", " Fed"), ("Understood", "Roger"),
    (" a little ", " a bit "), (" perhaps ", " maybe "), (" because ", " since "),
    (" however ", " but "), (" though ", ""), (" indeed ", " "),
]


def mech_fit(s, budget):
    """Meaning-preserving mechanical trim: contractions + filler removal."""
    if bl(s) <= budget:
        return s
    cur = s
    for a, b in MSUBS:
        if bl(cur) <= budget:
            break
        cur = cur.replace(a, b)
    cur = re.sub(r" +", " ", cur)
    cur = re.sub(r" +\n", "\n", cur).replace(" \"", "\"")
    return cur if bl(cur) < bl(s) else s


def call(system, user):
    body = json.dumps({
        "model": "deepseek-v4-pro",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2, "max_tokens": 8000,
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
            return json.load(r)["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(3 * (attempt + 1)); continue
            raise RuntimeError("HTTP %d: %s" % (e.code, e.read().decode()[:200]))


SYS = (
    "You shorten English game-dialogue lines to fit a HARD character limit, for a "
    "Super Robot Taisen Z fan-translation. Input: JSON object id -> "
    "{jp, limit, current, current_len, must_cut}. For each id: `current` is an English "
    "line that is TOO LONG at `current_len` characters; you must return a shorter "
    "rewrite of at most `limit` characters (count every character including spaces and "
    "the speaker name and newlines). You MUST cut at least `must_cut` characters versus "
    "`current` -- be aggressive: drop adjectives, filler, and redundant words; use "
    "contractions; keep only the core meaning. RULES: keep the speaker name + first "
    "newline; keep meaning and character voice; preserve $n $F $f $c placeholders "
    "exactly; ASCII only (no em-dash, no smart quotes, use '..' not the ellipsis char). "
    "Shorter is safe -- going well under the limit is fine. Return ONLY a JSON object "
    "id -> shortened English."
)


def main():
    n = int(sys.argv[1])
    p = 'rec%03d_en.py' % n
    s = u.spec_from_file_location('m%d' % n, p); m = u.module_from_spec(s); s.loader.exec_module(m)
    T = dict(m.T)
    wk = {r['i']: r for r in json.load(open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))}

    calls = [0]
    max_calls = 40  # hard cap so the fit loop can never run away

    def fit_chunk(ids):
        if calls[0] >= max_calls:
            return {}
        calls[0] += 1
        payload = {str(i): {"jp": wk[i]['jp'], "limit": wk[i]['budget'],
                            "current": T[i], "current_len": bl(T[i]),
                            "must_cut": max(3, bl(T[i]) - wk[i]['budget'] + 4)}
                   for i in ids}
        try:
            return _dm.parse_obj(call(SYS, json.dumps(payload, ensure_ascii=False)))
        except Exception as e:
            print("  parse fail: %s" % str(e)[:60])
            return {}

    with ThreadPoolExecutor(max_workers=12) as ex:
        for rnd in range(2):
            if calls[0] >= max_calls:
                break
            over = [i for i in T if i in wk and bl(T[i]) > wk[i]['budget']]
            if not over:
                break
            print("round %d: %d over" % (rnd + 1, len(over)))
            batches = [over[c:c + 20] for c in range(0, len(over), 20)]
            for out in ex.map(fit_chunk, batches):
                for k, v in out.items():
                    v = sanitize(v)
                    i = int(k)
                    if i not in wk:
                        continue
                    if bl(v) <= wk[i]['budget']:
                        T[i] = v
                    elif bl(v) < bl(T[i]):
                        T[i] = v  # keep the shorter attempt even if still over

    # final mechanical trim for anything DeepSeek couldn't fit
    for i in list(T):
        if i in wk and bl(T[i]) > wk[i]['budget']:
            T[i] = mech_fit(T[i], wk[i]['budget'])

    lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue (DeepSeek).""" ' % n,
             "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    over = [(i, bl(T[i]), wk[i]['budget']) for i in T if i in wk and bl(T[i]) > wk[i]['budget']]
    print("rec%03d final over: %d %s" % (n, len(over), over[:8]))


if __name__ == "__main__":
    main()
