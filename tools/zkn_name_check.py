# -*- coding: utf-8 -*-
"""Cross-check every LIBRARY name against the glossary DB, by Japanese key.

Three outcomes per name field:

  CONFLICT  the DB has this Japanese name and the library spells it differently
            -> the library is wrong, fix it
  MISSING   the DB has no entry for this Japanese name
            -> research it and add it (BASE_RULES: never invent a spelling)
  OK        library matches the DB

Names are matched on the JAPANESE (analysis/zkn_jp.json), never on the English,
because the whole point is to catch English that drifted.

Dialogue frequency is reported for every MISSING name so research can be
prioritised - a name used 900 times matters more than one used twice.

Usage: zkn_name_check.py <iso> [--conflicts | --missing | --all] [--min N]
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE
from zkn_audit import read_region, fields

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_TAGS = {"PT": ("CHFN", "CHNN"), "RT": ("RBTN", "PLTN"), "KW": ("WORD",)}


def load_db():
    db = {}
    for fn in ("glossary.json",):
        p = os.path.join(WORK, "analysis", fn)
        if os.path.exists(p):
            db.update(json.load(io.open(p, encoding="utf-8")))
    return db


def dialogue_text(iso):
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()
    return b"".join(bytes(d) for h, d in items if d is not None).decode("cp932", "ignore")


def main():
    iso = sys.argv[1]
    mode = "--all"
    for a in sys.argv[2:]:
        if a.startswith("--") and a != "--min":
            mode = a
    minf = 0
    if "--min" in sys.argv:
        minf = int(sys.argv[sys.argv.index("--min") + 1])

    db = load_db()
    jp = json.load(io.open(os.path.join(WORK, "analysis", "zkn_jp.json"),
                           encoding="utf-8"))
    dlg = dialogue_text(iso)
    conflicts, missing, ok = [], [], 0

    for key in ("PT", "RT", "KW"):
        tags = NAME_TAGS[key]
        for ri, rec in read_region(iso, key):
            cur = dict(fields(rec))
            src = jp.get(key, {}).get(str(ri), {})
            for tag in tags:
                j = (src.get(tag) or "").strip()
                e = (cur.get(tag) or "").strip()
                if not j or not e:
                    continue
                if j in db:
                    if db[j].strip() != e:
                        conflicts.append((key, ri, tag, j, e, db[j]))
                    else:
                        ok += 1
                else:
                    freq = len(re.findall(re.escape(e), dlg)) if e else 0
                    missing.append((key, ri, tag, j, e, freq))

    print("library name fields checked : %d" % (ok + len(conflicts) + len(missing)))
    print("  match the DB              : %d" % ok)
    print("  CONFLICT with the DB      : %d" % len(conflicts))
    print("  no DB entry (MISSING)     : %d" % len(missing))

    if mode in ("--all", "--conflicts") and conflicts:
        print("\n=== CONFLICTS - library disagrees with the DB ===")
        for key, ri, tag, j, e, want in conflicts:
            print("  %s rec%-4d %-4s %-22s library=%-22s db=%s" % (key, ri, tag, j, e, want))

    if mode in ("--all", "--missing") and missing:
        missing.sort(key=lambda x: -x[5])
        print("\n=== MISSING from the DB (by dialogue frequency) ===")
        shown = 0
        for key, ri, tag, j, e, freq in missing:
            if freq < minf:
                continue
            print("  %s rec%-4d %-4s %-22s english=%-24s dlg=%d"
                  % (key, ri, tag, j, e, freq))
            shown += 1
            if shown >= 60:
                print("  ... %d more" % (len(missing) - shown))
                break


if __name__ == "__main__":
    main()
