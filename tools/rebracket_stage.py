# -*- coding: utf-8 -*-
u"""Put the japanese corner brackets back on every spoken line, and turn any
ASCII "..." speech into 「...」.

WHY, having argued the other way. debracket_stage.py's header says the brackets
"do no work in the engine ... they are purely visual". That was measured in the
dialogue box, and in the box it is true - the renderer takes field line 1 as the
name plate, so the brackets sit inside the body doing nothing.

THE BACK LOG IS A DIFFERENT RENDERER. A live PINE session established that it
"draws the RAW record strings (never setText-converted)" (patch_backlog.py), and
it has no name plate: it prints the name line and the body lines as one run. A
three-way test on consecutive lines of the Titans corridor scene settled what
that means:

    Emma      bare        name drawn WHITE  - reads as a sentence fragment
    Kacricon  "ASCII"     name drawn WHITE  - speech delimited, name is not
    Jerid     「KAGI」      name drawn ORANGE - the engine colours it

So 「」 is load-bearing after all: it is the only form that makes the engine
colour the speaker name. corridor_polish.py had recorded exactly this ("also
turns the speaker name blue - engine behavior") and it was right. The check
itself is not an inline constant - the backlog's scanner at 0x221030 takes its
delimiter from a gp-relative global (`lb a0,-32412(gp)`), which is why grepping
the code for 0x8175 found nothing.

WHAT THIS DOES, per row, where the JAPANESE has 「 and ours does not:
  * strips a wrapping ASCII "..." if present,
  * wraps the speech in 「」,
  * re-flows the body with debracket_stage's own DP wrapper so the added
    4 columns (or 2, from quotes) do not push a line over the box.

Rows carrying $n / $c / $F are NOT re-flowed - a placeholder expands to a name
of unknown length at runtime and the shipped breaks already allow for it - so
they only get the brackets added to the first and last body line.

Nothing moves: every field is rewritten inside its own slot and NUL-padded.
A row whose slot cannot take the extra bytes, or that will not fit 3 lines, is
REPORTED rather than relocated - relocating past a record's end is what caused
the stage 29 crash (see the 0.9.34 entry).

Usage: rebracket_stage.py <iso> [--write] [--only REC]
"""
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from debracket_stage import cols, widest, wrap_balanced, WIDTH, MAXLINES, OPEN, CLOSE

SEC = 2048
LBA, SIZE = 1651029, 3910128
BASE = 0x7566F0
JP_ISO = "iso/srwz.bin"
QUOTE = u'"'


def _compress(job):
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(data)
    return ri, blob


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def slot_at(b, off):
    z = b.find(b"\x00", off)
    if z < 0:
        return None, None
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def pair(eb, jb):
    """english offset -> japanese offset, THROUGH THE POINTER TABLE."""
    out = {}
    for p in range(0, min(len(eb), len(jb)) - 4, 4):
        ve = struct.unpack_from("<I", eb, p)[0] - BASE
        vj = struct.unpack_from("<I", jb, p)[0] - BASE
        if 0 <= ve < len(eb) and 0 <= vj < len(jb) and ve not in out:
            out[ve] = vj
    return out


def convert(text, jp_text):
    """(field, reason). field is None when the row is left alone.

    EVERY budget is checked and the reason is RETURNED, not swallowed - a row
    that silently fails to gain its brackets is a row that still reads wrong in
    the backlog, and the count has to be visible.
      columns   : never wider than max(box 34, the japanese it replaces)
      lines     : never more than 3, which is what the box draws
      bytes     : must fit the field's own slot; nothing is ever relocated
    """
    if OPEN in text:
        return None, "already bracketed"
    # The japanese merely CONTAINING 「 is not enough. An encyclopedia entry
    # quotes a term mid-description - rec1's "An elite Earth Federation special
    # corps..." is one - and wrapping the whole description in speech marks
    # would be flatly wrong. Require the japanese body to be a single span that
    # OPENS with 「 and CLOSES with 」, the same test debracket_stage used on the
    # english going out.
    jl = jp_text.split(u"\n")
    jbody = u" ".join(jl[1:]).strip() if len(jl) > 1 else u""
    jbody = jbody.replace(u"　", u" ").strip()
    if not (jbody.startswith(OPEN) and jbody.endswith(CLOSE)):
        return None, "japanese body is not one quoted span"
    if jbody.count(OPEN) > 1:
        return None, "japanese has several quoted spans"
    lines = text.split(u"\n")
    if len(lines) < 2:
        return None, "no body"
    speaker, body = lines[0], [l for l in lines[1:] if l.strip()]
    if not body:
        return None, "no body"
    joined = u" ".join(body).strip()
    if joined.count(QUOTE) > 2:
        return None, "several quoted spans"
    if joined.startswith(QUOTE) and joined.endswith(QUOTE) and len(joined) > 1:
        inner = joined[1:-1].strip()
    elif QUOTE in joined:
        return None, "quote mid-sentence"
    else:
        inner = joined
    if not inner:
        return None, "empty"
    # never let a row come out wider than the japanese it replaces
    limit = max(WIDTH, widest(jp_text))
    if u"$" in text:
        # keep the shipped breaks; a placeholder may expand long
        kept = [l.replace(QUOTE, u"") for l in body if l.strip()]
        if not kept:
            return None, "empty"
        kept[0] = OPEN + kept[0].lstrip()
        kept[-1] = kept[-1].rstrip() + CLOSE
        if len(kept) > MAXLINES:
            return None, "over %d lines (placeholder row)" % MAXLINES
        w = max(cols(l) for l in kept)
        if w > limit:
            return None, "over budget: %d cols vs %d (placeholder row)" % (w, limit)
        return speaker + u"\n" + u"\n".join(kept), None
    got = wrap_balanced(OPEN + inner + CLOSE, limit)
    if not got:
        return None, "unwrappable"
    if len(got) > MAXLINES:
        return None, "over budget: needs %d lines, box draws %d" % (len(got), MAXLINES)
    w = max(cols(l) for l in got)
    if w > limit:
        return None, "over budget: %d cols vs %d" % (w, limit)
    return speaker + u"\n" + u"\n".join(got), None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = int(sys.argv[sys.argv.index("--only") + 1])

    jp = [(h, bytes(d)) for h, d in banlz.decompress_all(load(JP_ISO))
          if isinstance(h, int) and d is not None]
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytes(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    import collections
    touched, done, skipped = {}, 0, []
    reasons = collections.Counter()
    for ri in range(min(len(live), len(jp))):
        if only is not None and ri != only:
            continue
        eb, jb = bytearray(live[ri][1]), jp[ri][1]
        m = pair(bytes(eb), jb)
        changed = 0
        for eo, jo in sorted(m.items()):
            et, slot = slot_at(eb, eo)
            jt, _ = slot_at(jb, jo)
            if not et or not jt:
                continue
            if any(c < 0x0A for c in et):
                continue
            try:
                es, js = et.decode("cp932"), jt.decode("cp932")
            except UnicodeDecodeError:
                continue
            if OPEN not in js or u"\n" not in es:
                continue                   # japanese says this is not speech
            new, why = convert(es, js)
            if new is None:
                reasons[why or "?"] += 1
                if why and why.startswith("over budget"):
                    skipped.append((ri, eo, 0, 0, why, es))
                continue
            nb = new.encode("cp932")
            if len(nb) > slot:
                skipped.append((ri, eo, len(nb), slot,
                                "over budget: %d bytes vs slot %d" % (len(nb), slot), es))
                continue
            eb[eo:eo + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
            changed += 1
        if changed:
            touched[ri] = eb
            done += changed
            print("  rec%-4d %d row(s) re-bracketed" % (ri, changed))

    print("\nrows re-bracketed  : %d across %d record(s)" % (done, len(touched)))
    print("rows OVER BUDGET   : %d  (left alone - they still need editing)"
          % len(skipped))
    print("")
    print("--- every row NOT converted, by reason ---")
    for k, v in reasons.most_common():
        print("     %-34s %d" % (k[:34], v))
    kinds = collections.Counter(w.split(":")[1].split(" vs")[0].strip()
                                if ":" in w else w for _r, _o, _n, _s, w, _t in skipped)
    for k, v in kinds.most_common():
        print("     %-28s %d" % (k, v))
    for ri, eo, need, slot, why, es in skipped[:10]:
        print("   rec%-4d @%#08x  %s" % (ri, eo, why))
        print("        %s" % es.replace(u"\n", u" / ")[:88])

    if not touched:
        f.close()
        return 0
    if not write:
        # recompressing 200k-byte records is the slow part and it only exists
        # to prove the record still fits its slot - not worth paying twice
        print("\n(dry run - pass --write to apply)")
        f.close()
        return 0

    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, bytes(touched[ri])))
    got = {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 1)) as ex:
        for ri, blob in ex.map(_compress, [(r, n - h, d) for r, h, n, d in jobs]):
            got[ri] = blob
    for ri, hdr, nxt, d in jobs:
        blob = got[ri]
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot (%d > %d)" % (
            ri, len(blob), nxt - hdr)
        if write:
            raw[hdr:hdr + len(blob)] = blob
            for x in range(hdr + len(blob), nxt):
                raw[x] = 0
    if write:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("\nSTAGE written")
    else:
        print("\n(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
