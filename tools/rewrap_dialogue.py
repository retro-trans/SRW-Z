# -*- coding: utf-8 -*-
"""Re-wrap every over-wide dialogue string in STAGE.

The box is ~34 half-width COLUMNS and 「」 are FULLWIDTH (2 columns each),
but the original wrapper counted CHARACTERS - so any quoted first line of
exactly 34 characters is 35 columns and loses its last letter.  0.8.46
proved the fix on record 12; this does the rest.

Re-wrapping is BYTE-NEUTRAL (a line break just replaces a space), so every
string still fits its slot and nothing downstream moves.  A string is left
alone when the re-wrap would need a 4th line - those need their text
tightened first and are listed in analysis/rewrap_skipped.json.

Compression is the slow part (compress_record_optimal, ~1 KB/s), so the
records are compressed across a process pool; the splice and the
"nothing else changed" check still happen once, in the parent.

Usage: rewrap_dialogue.py <iso> [--dry-run] [--jobs N]
"""
import json
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz

LBA, SIZE, SECTOR = 1651029, 3910128, 2048
WIDTH, MAXLINES = 34, 3
Q0, Q1 = "「", "」"
SKIPPED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "analysis", "rewrap_skipped.json")


def cols(line):
    return sum(2 if ord(c) > 0x7f else 1 for c in line)


def rewrap(body):
    text = " ".join(l.strip() for l in body).strip()
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if cols(trial) <= WIDTH or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def strings(rec):
    """(start, end) of every NUL-terminated string in a record."""
    out, i, n = [], 0, len(rec)
    while i < n:
        if rec[i] == 0:
            i += 1
            continue
        j = rec.find(b"\x00", i)
        if j < 0:
            break
        out.append((i, j))
        i = j + 1
    return out


OVERRIDES = {}


def load_overrides(path):
    """{original full string (name + body): rewritten BODY text}.

    A rewrite is applied before wrapping, so the tightened line goes through
    the same greedy wrap and the same <= MAXLINES / <= WIDTH checks. The
    replacement is padded with NULs to the original slot, so the record's
    byte layout never moves - the same discipline SRVC needs for its
    sequence offsets.
    """
    import json as _json
    with open(path, encoding="utf-8") as fh:
        raw = _json.load(fh)
    out = {}
    for row in raw:
        if row.get("new"):
            out[row["old"]] = row["new"]
    return out


def fix_record(rec, idx=None):
    """-> (new_bytes, fixed, skipped_list) ; None if nothing changed.

    Skipped entries are logged as {rec, off, text} so the follow-up
    tightening pass can address them by address, not by search."""
    d = bytearray(rec)
    fixed, skipped = 0, []
    for s, e in strings(bytes(rec)):
        if b"\x81\x75" not in d[s:e] or b"\x81\x76" not in d[s:e]:
            continue                                   # not a quoted line
        try:
            t = bytes(d[s:e]).decode("cp932")
        except Exception:
            continue
        parts = t.split("\n")
        name, body = (parts[0], parts[1:]) if len(parts) > 1 else (None, parts)
        if not body:
            continue
        ov = OVERRIDES.get(t)
        if ov is not None:
            # a hand-tightened rewrite: keep whatever quote marks the
            # original carried, then wrap it like any other line
            lead = "「" if body[0].startswith("「") else ""
            tail = "」" if body[-1].endswith("」") else ""
            body = [lead + ov + tail]
        elif all(cols(l) <= WIDTH for l in body) and len(body) <= MAXLINES:
            continue
        new = rewrap(body)
        if len(new) > MAXLINES or any(cols(l) > WIDTH for l in new):
            skipped.append({"rec": idx, "off": s, "text": t})
            continue
        nt = "\n".join(([name] if name is not None else []) + new)
        nb = nt.encode("cp932")
        k = e
        while k < len(d) and d[k] == 0:
            k += 1
        slot = k - s
        if len(nb) >= slot:
            skipped.append({"rec": idx, "off": s, "text": t})
            continue
        d[s:s + slot] = nb + b"\x00" * (slot - len(nb))
        fixed += 1
    return (bytes(d), fixed, skipped) if fixed else (None, 0, skipped)


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    if "--overrides" in sys.argv:
        global OVERRIDES
        OVERRIDES = load_overrides(sys.argv[sys.argv.index("--overrides") + 1])
        print("overrides loaded: %d" % len(OVERRIDES))
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv \
        else max(1, (os.cpu_count() or 4) - 2)
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    hdrs = sorted(before)

    edited, total_fixed, all_skipped = {}, 0, []
    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        new, fixed, skipped = fix_record(bytes(dec), idx)
        all_skipped.extend(skipped)
        if new is not None:
            edited[idx] = (hdr, new)
            total_fixed += fixed
    print("records to rebuild: %d, strings re-wrapped: %d, left alone "
          "(would need a 4th line): %d"
          % (len(edited), total_fixed, len(all_skipped)))
    with open(SKIPPED, "w", encoding="utf-8") as fh:
        json.dump(all_skipped, fh, ensure_ascii=False, indent=0)
    if dry or not edited:
        f.close()
        return

    print("compressing %d records across %d processes..." % (len(edited), jobs))
    pool = multiprocessing.Pool(jobs)
    blobs = {}
    done = 0
    for idx, blob in pool.imap_unordered(
            _compress, [(i, p) for i, (_h, p) in edited.items()]):
        blobs[idx] = blob
        done += 1
        if done % 10 == 0 or done == len(edited):
            print("  %d/%d" % (done, len(edited)))
    pool.close()
    pool.join()

    out = bytearray(raw)
    over = []
    for idx, (hdr, _plain) in sorted(edited.items()):
        nxt = min([o for o in hdrs if o > hdr] or [SIZE])
        slot, blob = nxt - hdr, blobs[idx]
        if len(blob) > slot:                     # leave that record untouched
            over.append((idx, len(blob), slot))
            continue
        out[hdr:nxt] = blob + b"\x00" * (slot - len(blob))
    if over:
        print("OVERSIZE, left as-is: %s" % over)
    after = {o: bytes(x) for o, x in banlz.decompress_all(bytes(out))
             if x is not None}
    assert not [o for o in before if o not in after], "a record vanished"
    changed = sorted(o for o in before if after[o] != before[o])
    want = sorted(h for i, (h, _p) in edited.items()
                  if i not in {x[0] for x in over})
    assert changed == want, (len(changed), len(want))
    f.seek(LBA * SECTOR)
    f.write(bytes(out))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
