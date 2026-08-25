# -*- coding: utf-8 -*-
"""Prepare encyclopedia translation batches for agents.

Writes, per batch:
  analysis/zkn_work/<name>.txt    source blocks
  analysis/zkn_work/<name>_gloss.json   ONLY the names that occur in this batch

The sliced glossary matters: handing every agent the full 1,469-name map made
each one re-read 56 KB it mostly did not need, and each agent pays that from a
cold context. Slicing typically cuts it by an order of magnitude.

Usage: zkn_mkwork.py <key> <first> <count> <batchname> [<key> <first> <count> <name> ...]
       key = RT | PT | KW ; first/count index into the sorted record ids.
"""
import io
import json
import os
import sys

WORK = r"E:\Projects\SRW Z\_work"
OUT = os.path.join(WORK, "analysis", "zkn_work")


def main():
    a = os.path.join(WORK, "analysis")
    jp = json.load(io.open(os.path.join(a, "zkn_jp.json"), encoding="utf-8"))
    en = json.load(io.open(os.path.join(a, "zkn_en.json"), encoding="utf-8"))
    src = json.load(io.open(os.path.join(a, "name_source.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)

    args = sys.argv[1:]
    while args:
        key, first, count, name = args[0], int(args[1]), int(args[2]), args[3]
        args = args[4:]
        # "RT:DSC2" targets the second description field instead of DSCR.
        field = "DSCR"
        if ":" in key:
            key, field = key.split(":", 1)
        ids = sorted(jp[key], key=int)
        # skip records whose target field is already translated
        todo = [ri for ri in ids
                if field not in en.get(key, {}).get(ri, {})
                and jp[key][ri].get(field)]
        todo = todo[first:first + count]
        blocks = []
        corpus = []
        for ri in todo:
            e = jp[key][ri]
            t = e.get(field, "")
            if not t:
                continue
            ee = en.get(key, {}).get(ri, {})
            if key == "KW":
                head = "TERM: %s   | SERIES: %s" % (
                    ee.get("WORD", e.get("WORD", "")), ee.get("SRCE", e.get("SRCE", "")))
            elif key == "RT":
                head = "ROBOT: %s   | PILOT: %s   | SERIES: %s" % (
                    ee.get("RBTN", e.get("RBTN", "")), ee.get("PLTN", e.get("PLTN", "")),
                    ee.get("PRDC", e.get("PRDC", "")))
            else:
                head = "CHARACTER: %s   | SHORT: %s   | SERIES: %s   | VOICE: %s" % (
                    ee.get("CHFN", e.get("CHFN", "")), ee.get("CHNN", e.get("CHNN", "")),
                    ee.get("PRDC", e.get("PRDC", "")), e.get("ACTR", ""))
            blocks.append("===%s===\n%s\n%s\n" % (ri, head, t))
            corpus.append(t)
        body = "\n".join(corpus)
        gloss = {k: v for k, v in src.items() if k in body}
        io.open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8").write(
            "# Translate the DSCR text of each record below.\n"
            "# Block format: ===<id>=== / header with the OFFICIAL English names / Japanese.\n\n"
            + "\n".join(blocks))
        json.dump(gloss, io.open(os.path.join(OUT, name + "_gloss.json"), "w",
                                 encoding="utf-8"), ensure_ascii=False, indent=0)
        print("%-12s %s %s..%s  %d entries, glossary sliced %d -> %d names"
              % (name, key, todo[0] if todo else "-", todo[-1] if todo else "-",
                 len(blocks), len(src), len(gloss)))


if __name__ == "__main__":
    main()
