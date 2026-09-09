# -*- coding: utf-8 -*-
u"""Defeat conditions must not read as orders to the player.

The briefing panel has three boxes. Victory and SR Point list things the
player is told to DO, so "Defeat Sato." is right there. The Defeat box
lists things that happen TO the player, and we shipped those as orders
too: stage 46 reads

    Defeat
     1. Ally battleship lost
     2. Defeat Kira.

which tells the player to shoot down their own Kira. Worse, rec29's
victory condition is "Reduce Gekko-Goh HP to 10% or less" and its defeat
condition shipped as "Defeat the enemy unit." - an instruction to destroy
the one unit the player must keep alive.

WHY THE JAPANESE ALONE CANNOT CLASSIFY THESE. It is tempting to split on
grammar: an objective ends 「〜を撃墜する。」 (verb) and a trigger ends
「〜の撃墜。」 (noun). The verb form is indeed always an objective, but the
noun form is used in BOTH boxes - rec27's victory condition is
「敵の全滅。」 and rec48's is 「メカ鉄甲鬼の撃墜。」, both nouns. Position is
what decides, and the two ally-loss strings are the fixed landmark:

    味方戦艦の撃墜。          Ally battleship lost
    いずれかの味方ユニットの撃墜。  Any ally unit destroyed

are always the head of the defeat array. So: a slot AFTER that landmark
whose japanese is the NOUN form is a defeat trigger. Slots before it are
victory conditions, and the verb form after it is the SR condition that
follows the defeat array. Both halves of the test are needed - neither
alone is safe.

The rewrite is mechanical: "Defeat X." -> "X shot down.". 撃墜 is shot
down, and it reads as an event rather than an order next to the
"Ally battleship lost" line above it.

Everything that fits is written into its own bytes; the rest is moved to
free space with restore_brackets' allocator, which only uses NUL runs the
japanese holds text in (a japanese zero anywhere else is structure - see
fix_struct_intrusions).

Usage: fix_defeat_conditions.py <iso> <jp-iso> [--write] [--only REC]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X
import restore_brackets as RB

SEC, LBA, SIZE = 2048, 1651029, 3910128
BASE = EP.BASE
DOT = u"．"                      # the full-width period the panel uses

ANCHORS = (u"味方戦艦の撃墜。",
           u"いずれかの味方ユニ"
           u"ットの撃墜。")
# 「〜の撃墜。」 / 「〜いずれかの撃墜。」 - the noun form, no を…する
NOUN = re.compile(u"(の|いずれかの)"
                  u"撃墜。$")
LEAD = u"Defeat "


def target_at(b, p):
    u"""Text a pointer word at position p resolves to, or None."""
    if p + 4 > len(b):
        return None, 0
    v = struct.unpack_from("<I", b, p)[0] - BASE
    if not (0 <= v < len(b)):
        return None, 0
    t, room = EP.text_at(b, v)
    return t, v


def english(old):
    u"""'Defeat Kira．' -> 'Kira shot down．'"""
    core = old[len(LEAD):]
    dot = core.endswith(DOT)
    core = core.rstrip(DOT)
    if core == "the enemy unit":
        core = "Enemy unit"
    return core + u" shot down" + (DOT if dot else u"")


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    only = int(sys.argv[sys.argv.index("--only") + 1]) \
        if "--only" in sys.argv else None

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    g = open(jpiso, "rb")
    g.seek(LBA * SEC)
    jp = [d for h, d in banlz.decompress_all(g.read(SIZE))
          if isinstance(h, int) and d is not None]
    g.close()

    found = fixed = moved = 0
    nofit, riders = [], 0
    touched = {}
    for ri, (hdr, d) in enumerate(live):
        if only is not None and ri != only:
            continue
        eb = bytes(d)
        jb = bytes(jp[ri])
        n = min(len(eb), len(jb))
        anchors = []
        for p in range(0, n - 4, 4):
            jt, _ = target_at(jb, p)
            if jt in ANCHORS:
                anchors.append(p)
        if not anchors:
            continue
        pm = F.pointer_map(eb)
        smask = X.safe_mask(jb)
        protected = X.struct_words(jb, smask)
        gaps = RB.free_gaps(d, jb)
        before = {w: F.text_at(eb, v) for v, ws in pm.items() for w in ws
                  if w not in protected}
        moved_words = set()
        edited_words = set()
        changed = False
        for p in range(min(anchors) + 4, min(anchors) + 0x20, 4):
            jt, _ = target_at(jb, p)
            et, off = target_at(eb, p)
            if not jt or not et or not NOUN.search(jt):
                continue
            if not et.startswith(LEAD):
                continue
            found += 1
            new = english(et)
            nb = new.encode("cp932")
            z = d.find(b"\x00", off)
            # A pointer landing INSIDE the span we would overwrite blocks
            # the IN-PLACE write only - relocation repoints and leaves the
            # neighbour alone, so it must still be tried.
            rider = any(off < v <= off + len(nb) for v in pm if v != off)
            grow = off + len(nb) - z
            room_ok = grow <= 0 or all(
                d[x] == 0 and smask[x] for x in range(z, off + len(nb) + 1))
            if room_ok and not rider:
                d[off:off + len(nb)] = nb
                for x in range(off + len(nb), z):
                    d[x] = 0
                d[off + len(nb)] = 0
                edited_words.update(pm.get(off, []))
                fixed += 1
                changed = True
            elif RB.relocate(d, jb, off, nb, pm, protected, gaps,
                             moved_words, smask):
                fixed += 1
                moved += 1
                changed = True
            else:
                if rider:
                    riders += 1
                else:
                    nofit.append((ri, off, len(nb), z - off, et))
                continue
            print("  rec%-4d @%#07x  %-34r -> %r" % (ri, off, et, new))
        if changed:
            for w in protected:
                assert d[w:w + 4] == eb[w:w + 4], \
                    "rec%d structure pointer %#x moved" % (ri, w)
            nd = bytes(d)
            for w, t in before.items():
                nv = struct.unpack_from("<I", nd, w)[0] - F.BASE
                got = F.text_at(nd, nv)
                if w in moved_words or w in edited_words:
                    # changed on purpose; it must still resolve to something
                    assert got is not None, \
                        "rec%d word %#x stopped resolving" % (ri, w)
                else:
                    assert got == t, \
                        "rec%d word %#x no longer resolves to its text" % (ri, w)
            touched[ri] = bytes(d)

    print("")
    print("defeat conditions phrased as orders : %d" % found)
    print("rewritten                           : %d (%d moved to free space)"
          % (fixed, moved))
    print("skipped, pointer inside the field   : %d" % riders)
    print("did not fit (left as-is)            : %d" % len(nofit))
    for x in nofit[:20]:
        print("   rec%-4d @%#07x %d B > slot %d  %r" % x)
    if not touched or not write:
        if touched:
            print("")
            print("(dry run - pass --write to apply)")
        f.close()
        return 0

    for ri in sorted(touched):
        h = live[ri][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(touched[ri])
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(touched[ri])
        assert len(blob) <= nxt - h, "rec%d over slot" % ri
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("")
    print("STAGE written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
