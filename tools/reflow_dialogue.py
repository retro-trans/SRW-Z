# -*- coding: utf-8 -*-
"""Rewrap every STAGE dialogue body to the new proportional font's box width.

The old English was wrapped for the fixed 13px font (~34 cols). BIZ UDGothic is
proportional (advances 6..12px), so a line holds far more - we rewrap each
dialogue body to TARGET px (default 480; box proven to hold 546px, current
english maxes 407px). Fewer/tighter lines, same words.

SAFE by construction:
  * only fields whose body is 「..」 (a dialogue) are touched; the speaker plate
    (line 0) is preserved verbatim.
  * 《glossary links》 are kept whole (never split across a line break).
  * $-control codes ($n/$c = runtime name of UNKNOWN width) make a field SKIP,
    so we never mis-measure a line that expands at runtime.
  * result must be <= 3 body lines and <= the slot's byte budget, else SKIP.
  * reflow only removes/rebalances spaces+newlines, so bytes never grow.

Width model: half-width via the shipped advance table (0x78B960, advance-1);
full-width (kanji/「」/《》) = 21px; ASCII space = 6px.

Usage: reflow_dialogue.py <iso> [--target PX] [--write] [--limit N] [--dump FILE]
"""
import os, re, struct, sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
KO, KC = "「", "」"
# per-box-type pixel budgets (space=13 model). over-map box ~435px (Yassaba fit
# 431, Rand over 440); scene box ~530px (Sochie over 545). Targets sit below.
OVERMAP_PX, SCENE_PX = 415, 505
CHARS = [0x2E, 0x22, 0x27, 0x21, 0x2C, 0x2D, 0x3F] + list(range(0x30, 0x3A)) + \
        list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
LINK = re.compile(r"《[^》]*》")     # 《...》 kept whole


def load_adv(iso):
    f = open(iso, "rb"); f.seek(455 * SEC); elf = f.read(3471624); f.close()
    base = 0x34D770 + (0x78B960 - 0x78A070)
    tbl = elf[base:base + 69]
    return {chr(CHARS[i]): tbl[i] + 1 for i in range(69)}


def boxmap(d):
    """offset -> box type: 1 = over-map (32B table, type=1 at ptr+16), 0 = scene.
    The over-map box (~42 cols) is narrower than the scene big-box (~46 cols),
    verified in-game: Yassaba(over-map)=type1, Sochie(scene)=type0."""
    m = {}
    for p in range(0, len(d) - 4, 4):
        v = struct.unpack_from("<I", d, p)[0] - BASE
        if 0 <= v < len(d) and v not in m:
            t16 = struct.unpack_from("<I", d, p + 16)[0] if p + 20 <= len(d) else 0
            m[v] = 1 if t16 == 1 else 0
    return m


def width(s, adv):
    w = 0
    for ch in s:
        if ch == " ":
            w += 13
        elif ord(ch) < 128:
            w += adv.get(ch, 12)
        else:
            w += 21
    return w


def tokenize(body):
    """Split the inner body into wrap tokens, keeping 《links》 whole."""
    toks, i = [], 0
    for m in LINK.finditer(body):
        toks += body[i:m.start()].split(" ")
        toks.append(m.group())          # the whole 《...》 as one token
        i = m.end()
    toks += body[i:].split(" ")
    return [t for t in toks if t != ""]


def reflow(inner, target, adv):
    """inner = body text WITHOUT the outer 「」. Returns wrapped lines or None."""
    toks = tokenize(inner)
    lines, cur = [], ""
    for t in toks:
        cand = (cur + " " + t).strip()
        if not cur or width(cand, adv) <= target:
            cur = cand
        else:
            lines.append(cur); cur = t
    if cur:
        lines.append(cur)
    return lines


def slot_at(b, off):
    z = b.find(b"\x00", off)
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


GIANT = 160000   # optimal is intractable above this (rec0/rec139); those never overflow anyway


def _compress(job):
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        # These records already need optimal on the original disc (fast can't
        # reproduce the shipped slot). Reflow shrinks them but not enough for
        # fast, so use optimal - EXCEPT on a true giant, where optimal hangs;
        # there we leave the record unmodified (keep its original blob).
        if len(data) > GIANT:
            return ri, None, len(blob) - room
        blob = banlz.compress_record_optimal(data)
        if len(blob) > room:
            return ri, None, len(blob) - room
    return ri, blob, 0


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    target = int(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else 480
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    adv = load_adv(iso)

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    n_seen = n_reflow = n_skip_dollar = n_skip_lines = n_skip_same = n_skip_byte = 0
    touched, samples = {}, []
    n_over = n_scene = 0
    for ri, (hdr, d) in enumerate(live):
        i = 0
        changed = False
        bm = boxmap(d)
        while i < len(d):
            z = d.find(b"\x00", i)
            if z < 0:
                break
            field = bytes(d[i:z])
            nx = z
            while nx < len(d) and d[nx] == 0:
                nx += 1
            slot = nx - i - 1
            if b"\x81\x75" in field and b"\x81\x76" in field:   # 「 and 」
                try:
                    txt = field.decode("cp932")
                except UnicodeDecodeError:
                    i = z + 1; continue
                lines = txt.split("\n")
                # body must open with 「 and close with 」
                bstart = next((k for k, l in enumerate(lines) if l.startswith(KO)), None)
                if bstart is not None and lines[-1].rstrip().endswith(KC):
                    n_seen += 1
                    speaker = lines[:bstart]
                    body = " ".join(lines[bstart:])   # join to one flow
                    inner = body.strip()[1:-1].strip()   # drop 「 」
                    inner = re.sub(r"\s+", " ", inner)   # collapse spaces
                    if "$" in inner:
                        n_skip_dollar += 1
                    else:
                        over = bm.get(i, 1) == 1        # default over-map (narrow, safe)
                        tgt = OVERMAP_PX if over else SCENE_PX
                        wl = reflow(inner, tgt - 21, adv)   # -21 leaves room for 「/」
                        if wl is None or len(wl) > 3:
                            n_skip_lines += 1
                        else:
                            wl[0] = KO + wl[0]
                            wl[-1] = wl[-1] + KC
                            newbody = "\n".join(wl)
                            newfield = ("\n".join(speaker + [newbody]) if speaker
                                        else newbody)
                            nb = newfield.encode("cp932")
                            if nb == field:
                                n_skip_same += 1
                            elif len(nb) > slot:
                                n_skip_byte += 1
                            else:
                                d[i:i + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
                                changed = True
                                n_reflow += 1
                                n_over += over; n_scene += (not over)
                                if len(samples) < 12:
                                    samples.append((ri, txt, newfield))
                                if limit and n_reflow >= limit:
                                    break
            i = z + 1
        if changed:
            touched[ri] = d
        if limit and n_reflow >= limit:
            break

    print("dialogue fields seen: %d" % n_seen)
    print("  reflowed:        %d  (over-map %d / scene %d)" % (n_reflow, n_over, n_scene))
    print("  skip ($name):    %d" % n_skip_dollar)
    print("  skip (>3 lines): %d" % n_skip_lines)
    print("  skip (no change):%d" % n_skip_same)
    print("  skip (byte over):%d" % n_skip_byte)
    print("  records touched: %d" % len(touched))
    for ri, old, new in samples[:8]:
        print("  --- rec%d ---" % ri)
        print("   OLD: %r" % old.replace("\n", " / "))
        print("   NEW: %r" % new.replace("\n", " / "))
    if "--dump" in sys.argv:
        import json, io
        json.dump([{"rec": ri, "old": o, "new": n} for ri, o, n in samples],
                  io.open(sys.argv[sys.argv.index("--dump") + 1], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    if not write or not touched:
        if touched:
            print("\n(dry run - pass --write to apply)")
        f.close()
        return
    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, bytes(touched[ri])))
    got, over = {}, {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2)) as ex:
        for ri, blob, margin in ex.map(_compress, [(r, n - h, dd) for r, h, n, dd in jobs]):
            got[ri] = blob
            if blob is None:
                over[ri] = margin
    applied = 0
    for ri, hdr, nxt, dd in jobs:
        blob = got[ri]
        if blob is None:
            continue                       # overflow: keep original compressed bytes
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
        applied += 1
    if over:
        print("compress overflow, %d record(s) left unmodified: %s"
              % (len(over), ", ".join("rec%d(+%dB)" % (r, m) for r, m in sorted(over.items()))))
    print("records recompressed & applied: %d" % applied)
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "record layout changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written (%d records, %d lines reflowed)" % (len(touched), n_reflow))


if __name__ == "__main__":
    main()
