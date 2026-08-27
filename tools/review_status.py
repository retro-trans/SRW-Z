# -*- coding: utf-8 -*-
"""Track which scenario records a human has actually read.

Most of this translation is machine output that no person has checked - 141 of
the 205 records, by the count in CONTRIBUTING.md. That makes "has anyone read
this one?" the most useful question a contributor can ask, and until now there
was nowhere to record the answer, so two people could proofread the same record
and neither would know.

WHAT IS MEASURED AND WHAT IS DECLARED. The signals below are computed from the
image every time, so they cannot go stale. The review STATUS cannot be computed
- only a person knows whether they read something - so it is declared, and it
defaults to `unreviewed`. No record is marked as read on a guess: there is no
surviving record of which 64 were read, so this starts everything at unreviewed
rather than inventing a history.

    rows          dialogue rows in the record
    untranslated  rows still holding japanese - a hard defect, not an opinion
    over_width    rows wider than the 34-column box
    machine       rows DeepSeek flagged for later review (analysis/
                  deepseek_review.json), where that data exists

Usage:
  review_status.py <iso> --init            build/refresh signals for all records
  review_status.py --report                summary, and what to work on next
  review_status.py --mark 127 --by NAME [--status reviewed] [--note "..."]
"""
import io
import json
import os
import re
import struct
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "analysis", "review", "STATUS.json")
BASE = 0x7566F0
WIDTH = 34
KAGI = u"「"
CJK = re.compile(u"[぀-ヿ一-鿿]")
STATES = ("unreviewed", "in-progress", "reviewed", "needs-work")


def cols(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def texty(s):
    """Does this look like a line of script, rather than data that decoded?

    Without this the counts are badly wrong. A record's pointer table and its
    padding also decode as cp932, and a run of high bytes happily produces
    kanji - so junk scores as "untranslated dialogue". It reported 127
    untranslated rows in rec138 alone when the entire game has 480."""
    if len(s.strip()) < 3:
        return False
    if not re.search(u"[A-Za-z぀-ヿ一-鿿]", s):
        return False
    ok = sum(1 for c in s if c in "\n\t" or 32 <= ord(c) < 127 or ord(c) > 160)
    return ok >= len(s) * 0.85


def rows_of(rec):
    """Strings the pointer table actually points at - the rows the game draws."""
    b = bytes(rec)
    out = {}
    for p in range(0, len(b) - 4, 4):
        v = struct.unpack_from("<I", b, p)[0] - BASE
        if not (0 <= v < len(b)) or v in out:
            continue
        z = b.find(b"\x00", v)
        if z <= v or z - v > 1200:
            continue
        try:
            s = b[v:z].decode("cp932")
        except Exception:
            continue
        if texty(s):
            out[v] = s
    return out


def load():
    if os.path.exists(PATH):
        return json.load(io.open(PATH, encoding="utf-8"))
    return {"note": "Review status per scenario record. `status` is declared by "
                    "a human; every other field is computed from the image by "
                    "tools/review_status.py --init.",
            "records": {}}


def save(d):
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(
        json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True))


def init(iso):
    d = load()
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()
    mach = {}
    p = os.path.join(ROOT, "analysis", "deepseek_review.json")
    if os.path.exists(p):
        for k, v in json.load(io.open(p, encoding="utf-8")).items():
            m = re.search(r"(\d+)", k)
            if m:
                mach[str(int(m.group(1)))] = len(v.get("jp_untranslated") or [])
    for idx, (_hdr, plain) in enumerate(items):
        if plain is None:
            continue
        rs = rows_of(plain)
        if not rs:
            continue
        untr = sum(1 for s in rs.values() if CJK.search(s))
        wide = 0
        for s in rs.values():
            # Only SPEECH is bound to 34 columns. The scenario-chart recaps in
            # rec0 get a 56-column box, so measuring them against the dialogue
            # width reported 110 over-width rows in a record that is correct.
            if KAGI not in s:
                continue
            body = s.split("\n")[1:]
            if body and max(cols(b) for b in body) > WIDTH:
                wide += 1
        k = str(idx)
        rec = d["records"].get(k, {"status": "unreviewed", "reviewer": None,
                                   "date": None, "note": ""})
        rec.update({"rows": len(rs), "untranslated": untr, "over_width": wide,
                    "machine_flagged": mach.get(k, 0)})
        d["records"][k] = rec
    save(d)
    print("signals refreshed for %d records -> %s"
          % (len(d["records"]), os.path.relpath(PATH, ROOT)))


def report():
    d = load()
    R = d["records"]
    if not R:
        raise SystemExit("no data yet - run: review_status.py <iso> --init")
    by = {s: [k for k, v in R.items() if v.get("status") == s] for s in STATES}
    rows = sum(v.get("rows", 0) for v in R.values())
    done = sum(R[k].get("rows", 0) for k in by["reviewed"])
    print("records: %d   dialogue rows: %d" % (len(R), rows))
    for s in STATES:
        n = len(by[s])
        if n:
            print("   %-12s %3d records  %6d rows"
                  % (s, n, sum(R[k].get("rows", 0) for k in by[s])))
    print("   %-12s %.1f%% of rows read by a human" % ("coverage",
          100.0 * done / max(1, rows)))
    todo = [(v.get("untranslated", 0) + v.get("over_width", 0)
             + v.get("machine_flagged", 0), k, v)
            for k, v in R.items() if v.get("status") == "unreviewed"]
    todo.sort(reverse=True)
    print("\nunreviewed, worst signals first:")
    print("   %-6s %6s %6s %6s %6s" % ("rec", "rows", "untr", "wide", "flag"))
    for score, k, v in todo[:15]:
        print("   %-6s %6d %6d %6d %6d" % (k, v.get("rows", 0),
              v.get("untranslated", 0), v.get("over_width", 0),
              v.get("machine_flagged", 0)))


def mark():
    d = load()
    rec = sys.argv[sys.argv.index("--mark") + 1]
    who = sys.argv[sys.argv.index("--by") + 1] if "--by" in sys.argv else None
    st = sys.argv[sys.argv.index("--status") + 1] if "--status" in sys.argv \
        else "reviewed"
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
    when = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else None
    if st not in STATES:
        raise SystemExit("status must be one of: %s" % ", ".join(STATES))
    if st != "unreviewed" and not who:
        raise SystemExit("--by NAME is required: a review with no reviewer is "
                         "not a review")
    r = d["records"].setdefault(rec, {"rows": 0, "untranslated": 0,
                                      "over_width": 0, "machine_flagged": 0})
    r.update({"status": st, "reviewer": who, "date": when, "note": note})
    save(d)
    print("rec%s -> %s (%s)" % (rec, st, who or "-"))


def main():
    if "--report" in sys.argv:
        return report()
    if "--mark" in sys.argv:
        return mark()
    if "--init" in sys.argv:
        return init(sys.argv[1])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
