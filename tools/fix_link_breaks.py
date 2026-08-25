# -*- coding: utf-8 -*-
"""Re-wrap dialogue so glossary terms are never split across a line break.

A link's underline is drawn per text segment, so the linker refuses to wrap a
term that straddles a break - those terms ship as plain text and the reader
never sees the link. 77 occurrences of 13 terms are in that state ("Glory
Star" 30 times, "Scub Coral" 14, "Earth Alliance" 7...).

This pass re-wraps only the affected strings, with the single extra rule that
a term may not be broken. Everything else is unchanged: same greedy wrap, same
34-column / 3-line box, and the same byte-neutral splice (the replacement is
padded to the original slot, so nothing downstream moves). A string that
cannot fit with the term intact is left exactly as it is.

Run the linker afterwards to actually wrap the recovered terms.

Usage: fix_link_breaks.py <iso> [--dry-run]
"""
import importlib.util
import multiprocessing
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES, cols, strings

NBSP = "￿"          # private stand-in for "do not break here"


def glossary_terms():
    spec = importlib.util.spec_from_file_location(
        "aq", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "apply_quotes_links_all.py"))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception:
        pass
    out = []
    for variants in getattr(m, "GLOSS", {}).values():
        for v in variants:
            if " " in v:
                out.append(v)
    return sorted(set(out), key=len, reverse=True)


TERMS = glossary_terms()


def rewrap_keeping(text, terms):
    """Greedy wrap, but never break inside one of `terms`."""
    glued = text
    for t in terms:
        glued = glued.replace(t, t.replace(" ", NBSP))
    words, lines, cur = glued.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cols(trial.replace(NBSP, " ")) <= WIDTH or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return [l.replace(NBSP, " ") for l in lines]


def fix_record(rec, terms):
    d = bytearray(rec)
    fixed = 0
    for s, e in strings(bytes(rec)):
        if b"\x81\x75" not in d[s:e]:
            continue
        try:
            t = bytes(d[s:e]).decode("cp932")
        except UnicodeDecodeError:
            continue
        parts = t.split("\n")
        name, body = (parts[0], parts[1:]) if len(parts) > 1 else (None, parts)
        if not body:
            continue
        flat = " ".join(l.strip() for l in body)
        # only strings where a term is currently broken
        broken = [x for x in terms
                  if re.search(re.escape(x).replace(r"\ ", r"\n"), t)]
        if not broken:
            continue
        new = rewrap_keeping(flat, terms)
        if len(new) > MAXLINES or any(cols(l) > WIDTH for l in new):
            continue                      # cannot keep it whole - leave alone
        nt = "\n".join(([name] if name is not None else []) + new)
        nb = nt.encode("cp932")
        k = e
        while k < len(d) and d[k] == 0:
            k += 1
        slot = k - s
        if len(nb) >= slot:
            continue
        d[s:s + slot] = nb + b"\x00" * (slot - len(nb))
        fixed += 1
    return (bytes(d), fixed) if fixed else (None, 0)


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    print("glossary terms with a space: %d" % len(TERMS))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}

    edited, total = {}, 0
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        new, n = fix_record(bytes(dec), TERMS)
        if new is not None:
            edited[idx] = (hdr, new)
            total += n
    print("records to rebuild: %d, strings re-wrapped to keep a term whole: %d"
          % (len(edited), total))
    if dry or not edited:
        return

    jobs = max(1, (os.cpu_count() or 4) - 2)
    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    packed = dict(pool.map(_compress, [(i, d) for i, (h, d) in edited.items()]))
    pool.close(); pool.join()

    for idx, (hdr, plain) in edited.items():
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "record %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0

    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sum(1 for o in before if check[o] != before[o])
    assert changed == len(edited), "unexpected records changed (%d)" % changed
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % changed)


if __name__ == "__main__":
    main()
