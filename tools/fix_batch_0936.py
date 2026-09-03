# -*- coding: utf-8 -*-
u"""Screenshot-reported text batch for 0.9.36: five renames and six rewrites.

Every edit is IN PLACE - each string is rewritten inside its own slot and
NUL-padded to the same extent, so no offset moves and no pointer changes. That
matters more than usual here: a STAGE string that lands at or past its original
japanese record end renders blank or crashes (see the 0.9.34 entry), and the
only way to stay clear of that is to never move one.

RENAMES (checked against the japanese, not guessed)

  Elder    -> Eldar     エルダー, the alien empire in God Sigma. 529 hits, and
                        the build already said Eldar in 58 places, so it was
                        inconsistent with itself. All 158 distinct strings were
                        read first: every one is the race, none is the English
                        word "elder", so a blanket rename is safe. Same length,
                        so nothing reflows.
  Kilaken  -> Kiraken   キラケン, God Sigma's third pilot. ONE stray against 220
                        correct - and the two sit in the same conversation, so
                        Tetsuya answers a character whose name just changed
                        spelling mid-scene.
  Kirakenn -> Kiraken   doubled n, once, in the stage-0 synopsis.
  Suesson  -> Sweatson  スエッソン. COMPDATA already said Sweatson in all three
                        places; only STAGE said Suesson, 39 times. Grows by a
                        byte, and three lines had no spare - those three get a
                        matching trim below rather than a relocation.
  Majin    -> Mazin     マジンパワー is Mazinger's. The search grid already said
                        "Mazin Pwr" while the full list said "Majin Power"
                        (魔神, a different reading). Same length.

REWRITES - see CHANGELOG for the japanese and the reasoning.

Usage: fix_batch_0936.py <iso> [--write]
"""
import os
from concurrent.futures import ProcessPoolExecutor
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
STAGE_LBA, STAGE_SIZE = 1651029, 3910128
COMP_LBA, COMP_NSEC = 1823000, 74
SRVC_LBA, SRVC_SIZE = 1313214, 2915108
BOX = 38                      # battle-caption column cap

# ---------------------------------------------------------------- rewrites
# (record, offset, old, new). The old text is asserted before anything is
# written, so a mismatch fails the run instead of corrupting a record.
REWRITE = [
    # Holland - "crush that" was そんな奴ら, "guys like that", not a thing;
    # らしいな (the inference) was dropped; 手先 is a pawn, not a puppet.
    (69, 0x15880,
     u"Holland\n\"You've become the puppets of\nsomeone painting the world one\n"
     u"color! We'll crush that here!\"",
     u"Holland\n\"Seems you've become the pawns\nof the guy painting over the\n"
     u"world! We'll crush you here!\""),

    # Dewey - 人類の殲滅 is the ANNIHILATION of mankind, not "man's cleansing";
    # に過ぎません ("nothing more than") and the hedge in 抗体とでも言うべき
    # were both dropped. Kte -> Kute (クテ).
    (68, 0xdd66,
     u"Dewey\n「The Kte-class are a gateway.\nSoon antibodies appear and man's\n"
     u"cleansing begins.」",
     u"Dewey\n「The Kute-class are but a gate.\nSoon so-called antibodies appear\n"
     u"and mankind's annihilation begins.」"),

    # President x2 - 「ザフトに…落とされ」 is the suffering passive: the
    # Federation had ITS new weapon shot down BY ZAFT. The English had ZAFT
    # dropping a weapon ON them, which also merges the two separate reasons for
    # the withdrawal (the weapon, and the riots in the rear). Also 「…。」 had
    # come out as two bare periods.
    (67, 0x2410,
     u"President\n「ZAFT dropped their prized new\nweapon on them, their rear's in\n"
     u"uproar.. No wonder they retreat.」",
     u"President\n「ZAFT downed their prized new\nweapon, and their rear's in that\n"
     u"uproar... They must pull back.」"),
    (96, 0x2210,
     u"President\n「ZAFT dropped their prized new\nweapon on them, their rear's in\n"
     u"uproar.. No wonder they retreat.」",
     u"President\n「ZAFT downed their prized new\nweapon, and their rear's in that\n"
     u"uproar... They must pull back.」"),

    # Ziene - 「させない…とでも言うのかい？」 is Ziene quoting the line back at
    # them ("'I won't let you'... is that what you mean to say?"), not asking
    # "stop it?". 言う is say, not think. 無理だよ is "you're not up to it".
    (54, 0x11620,
     u"Ziene\n「Stop it? Is that what you think?\nBut you can't do it.」",
     u"Ziene\n「\"I won't let you\"... is that it?\nBut you haven't got it in you.」"),

    # Tetsuya - Kilaken -> Kiraken, and 容赦はしない is "I won't show mercy",
    # which is a good deal harder than "I won't hold back".
    (54, 0xf0d0,
     u"Tetsuya\n「Don't get me wrong, Kilaken. If\nthat woman Four comes, I won't\n"
     u"hold back.」",
     u"Tetsuya\n「Don't get me wrong, Kiraken. If\nthat woman Four comes at us, I\n"
     u"won't show mercy.」"),

    # Banjo - さあ行くぞ is him starting the attack, not "now then"; 末端の君達
    # ("you of the lower ranks") had lost its preposition, and これも出会った不運
    # ("running into me is your misfortune too") had been clipped to "bad luck".
    # Line 1 stays at 32 columns: 34 is the widest this box is PROVEN to render
    # (the President's third line), and the natural "Here we go," lands on 35.
    (69, 0x178f0,
     u"Banjo\n「Now then, New Earth Federation!\n…Striking you rank and file won't\n"
     u"truly solve this, but bad luck!」",
     u"Banjo\n「Let's go, New Earth Federation!\n…Beating rank and file like you\n"
     u"solves nothing, but hard luck!」"),

    # Loran - 「もう出来ないんでしょうか」 is "can we no longer...", a wistful
    # question about the present. "never join hands again like before" reads as
    # word salad; the JP is 以前のように ("the way we used to").
    (69, 0x17be0,
     u"Loran\n「Can we... never join hands again\nlike before...?」",
     u"Loran\n「Can we never join hands the way\nwe used to, ever again...?」"),
]

# Suesson -> Sweatson costs a byte and these three strings had none spare.
# Trimmed in the body instead of relocating the string.
TRIM = [
    (54, 0x10bf0, u"This is not a drill. Repeat,", u"This is no drill. Repeat,"),
    (54, 0x11870, u"Guess gravity just doesn't",   u"Guess gravity doesn't"),
    (54, 0x15fbc, u"the war we've waited",         u"the war we waited"),
]

# SRVC strings tile their block with no padding, so a caption may not gain a
# single byte without a repack - and Suesson -> Sweatson gains one. These seven
# therefore pay for it inside the same line. Lengths are asserted equal.
#   "house" -> "clan" is not a fudge: ギンガナム家 is the Ghingnham clan.
SRVC_REWRITE = [
    # The clipped Hyakki caption. 「お前達も知ったはずだ…\n人間の心に潜む闇をな！」
    # is TWO lines; ours was one 40-column line against a 38-column cap, so the
    # game cut it at "the dark in the hear".
    #
    # THE SEPARATOR IS NOT 0x0A. SRVC stores a LITERAL backslash-n (5C 6E) and
    # converter 0x2EA280 turns it into 0x0A when it fills the display buffer -
    # that strstr against 0x0043FF70 is exactly what it is looking for. So the
    # break costs two bytes where the space cost one, and a caption may not
    # grow: SRVC strings tile their block with nothing between them. (They may
    # SHRINK - the index addresses each string, so trailing dead bytes are
    # simply never read.) One character pays for it; the closing "!" goes.
    (b'"You know too\x85\x40\x85\x40\x85\x40 the dark in the heart!"',
     b'"You know too\x85\x40\x85\x40\x85\x40\\nthe dark in the heart"'),
    # and the same again from the bad 0x0A form, so this is re-runnable
    (b'"You know too\x85\x40\x85\x40\x85\x40\nthe dark in the heart!"',
     b'"You know too\x85\x40\x85\x40\x85\x40\\nthe dark in the heart"'),

    (b'"How long will you drill, Suesson!"',
     b'"How long will you drill Sweatson!"'),
    (b'"Suesson! That\'s no way to lead a unit!"',
     b'"Sweatson! No way to lead a unit, that!"'),
    (b'"Ghingnham\'s house doesn\'t know\\nreal combat, Suesson Stello!"',
     b'"Ghingnham\'s clan doesn\'t know\\nreal combat, Sweatson Stello!"'),
]

RENAME = [
    (b"Kirakenn", b"Kiraken"),
    (b"Kilaken",  b"Kiraken"),
    (b"Elder",    b"Eldar"),
    (b"Suesson",  b"Sweatson"),
    (b"Majin Power", b"Mazin Power"),
]


def _compress(job):
    """(ri, room, data) -> (ri, blob). Module level so it can be pickled."""
    ri, room, data = job
    blob = banlz.compress_record(data)
    if len(blob) > room:
        blob = banlz.compress_record_optimal(data)
    return ri, blob


def slot_at(b, off):
    """Bytes usable for text at off, excluding the terminator."""
    z = b.find(b"\x00", off)
    if z < 0:
        return None, None
    k = z
    while k < len(b) and b[k] == 0:
        k += 1
    return bytes(b[off:z]), k - off - 1


def put(d, off, new):
    """Write new over the string at off, NUL-filling the rest of its slot."""
    cur, slot = slot_at(d, off)
    assert cur is not None, "no string at %#x" % off
    assert len(new) <= slot, "%#x needs %d bytes, slot %d" % (off, len(new), slot)
    d[off:off + slot + 1] = new + b"\x00" * (slot + 1 - len(new))


def rename_all(d, stats):
    """Apply RENAME to every string in the record, in place."""
    n = 0
    for old, new in RENAME:
        pos = 0
        while True:
            # search the live bytearray: copying the whole record per match
            # turned this into an O(n^2) crawl across 205 records
            k = d.find(old, pos)
            if k < 0:
                break
            pos = k + len(new)
            if len(old) == len(new):
                # Same length needs no string bounds at all - splice the bytes
                # where they sit. Going through the slot logic here got 167 of
                # 529 Elders: speaker names are prefixed with a 0x0C colour
                # code, so reconstructing "the string" from the previous NUL
                # yielded b"\x0cElder" and the control-byte guard threw it out.
                # 0x0C is in-band text markup, not bytecode.
                d[k:k + len(old)] = new
                n += 1
                stats[old] = stats.get(old, 0) + 1
                continue
            s = d.rfind(b"\x00", 0, k) + 1
            cur, slot = slot_at(d, s)
            if cur is None or any(c < 0x09 for c in cur):
                continue                      # bytecode that merely reads as text
            nt = cur.replace(old, new)
            if nt == cur or len(nt) > slot:
                if len(nt) > slot:
                    stats.setdefault("skipped", []).append((s, old, len(nt), slot))
                continue
            put(d, s, nt)
            n += 1
            stats[old] = stats.get(old, 0) + 1
    return n


def rewrite_stage(raw, write, stats):
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    touched = {}

    def rec(ri):
        if ri not in touched:
            touched[ri] = bytearray(live[ri][1])
        return touched[ri]

    for ri, off, old, new in REWRITE:
        d = rec(ri)
        ob, nb = old.encode("cp932"), new.encode("cp932")
        cur, slot = slot_at(d, off)
        if cur == nb:
            continue                          # already applied; re-runnable
        assert cur == ob, ("rec%d @%#x does not hold the expected text\n  have %r\n  want %r"
                           % (ri, off, cur, ob))
        put(d, off, nb)
        stats.setdefault("rewrites", []).append((ri, off, len(ob), len(nb), slot))

    for ri, off, old, new in TRIM:
        d = rec(ri)
        cur, slot = slot_at(d, off)
        ob, nb = old.encode("cp932"), new.encode("cp932")
        if ob not in cur and nb in cur:
            continue                          # already trimmed; re-runnable
        assert ob in cur, "rec%d @%#x has no %r" % (ri, off, ob)
        put(d, off, cur.replace(ob, nb))
        stats.setdefault("trims", []).append((ri, off))

    for ri in range(len(live)):
        d = rec(ri)
        before = bytes(d)
        rename_all(d, stats)
        if bytes(d) == before and ri not in [x[0] for x in REWRITE] \
                and ri not in [x[0] for x in TRIM]:
            del touched[ri]

    print("STAGE: %d record(s) changed" % len(touched))
    # Records are independent, so compress across all cores - the same reason
    # build_stage_par.py exists. banlz is pure python and costs ~20s a record;
    # 37 of them one at a time is a quarter of an hour of nothing happening.
    jobs = []
    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        jobs.append((ri, hdr, nxt, bytes(touched[ri])))
    done = {}
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 1)) as ex:
        for ri, blob in ex.map(_compress, [(ri, nxt - hdr, d) for ri, hdr, nxt, d in jobs]):
            done[ri] = blob
            print("   rec%-3d -> %d bytes" % (ri, len(blob)))
    for ri, hdr, nxt, d in jobs:
        blob = done[ri]
        assert blob is not None and len(blob) <= nxt - hdr, \
            "rec%d grew past its slot (%s > %d)" % (
                ri, len(blob) if blob else "fail", nxt - hdr)
        if write:
            raw[hdr:hdr + len(blob)] = blob
            for x in range(hdr + len(blob), nxt):
                raw[x] = 0
    if write:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
    return len(touched)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    stats = {}
    f = open(iso, "r+b" if write else "rb")

    # ---- STAGE ----
    f.seek(STAGE_LBA * SEC)
    stage = bytearray(f.read(STAGE_SIZE))
    rewrite_stage(stage, write, stats)
    if write:
        f.seek(STAGE_LBA * SEC)
        f.write(bytes(stage))

    # ---- COMPDATA ----
    f.seek(COMP_LBA * SEC)
    craw = bytearray(f.read(COMP_NSEC * SEC))
    clive = [(h, d) for h, d in banlz.decompress_all(bytes(craw))
             if isinstance(h, int) and d is not None]
    hdr, cd = clive[0][0], bytearray(clive[0][1])
    n = rename_all(cd, stats)
    print("COMPDATA: %d string(s) changed" % n)
    if n:
        blob = banlz.compress_record(bytes(cd))
        if len(blob) > COMP_NSEC * SEC:
            blob = banlz.compress_record_optimal(bytes(cd))
        assert hdr + len(blob) <= COMP_NSEC * SEC, "COMPDATA overflows its slot"
        if write:
            craw[hdr:hdr + len(blob)] = blob
            f.seek(COMP_LBA * SEC)
            f.write(bytes(craw))

    # ---- SRVC caption ----
    # 「お前達も知ったはずだ…\n　人間の心に潜む闇をな！」 is TWO lines; ours
    # collapsed to one 40-column line against a 38-column cap, so the game
    # clipped it mid-word ("...the dark in the hear"). The three bytes before
    # "the dark" are 85 40 x3 - our private half-width period glyphs, i.e. the
    # ellipsis, rendering correctly. Only the space after it is wrong: turning
    # that one byte into a newline restores the japanese's own line break and
    # costs nothing, so SRVC needs no repack.
    f.seek(SRVC_LBA * SEC)
    srvc = bytearray(f.read(SRVC_SIZE))
    # The battle captions are their own surface and verify_terms reads them
    # straight out of the image, so the renames have to land here too. Only the
    # same-length ones can: SRVC strings tile their block with no padding
    # between them, so nothing may grow by even a byte without a repack.
    for old, new in SRVC_REWRITE:
        assert len(old) == len(new), "caption rewrite changes length: %r" % old
        n = 0
        p = 0
        while True:
            k = srvc.find(old, p)
            if k < 0:
                break
            srvc[k:k + len(old)] = new
            p = k + len(new)
            n += 1
        if n:
            # 0x85xx are our private half-width glyphs and decode to nothing a
            # console codepage can print - show them as the '.' they render as
            shown = new.replace(b"\x85\x40", b".").split(b"\\n")[0]
            print("SRVC: %d x %s" % (n, shown.decode("ascii", "replace")))

    for old, new in RENAME:
        if len(old) != len(new):
            continue
        n = 0
        p = 0
        while True:
            k = srvc.find(old, p)
            if k < 0:
                break
            srvc[k:k + len(old)] = new
            p = k + len(new)
            n += 1
        if n:
            print("SRVC: %-12s -> %-12s %d" % (old.decode(), new.decode(), n))
            stats[old] = stats.get(old, 0) + n

    # Every caption we touched must sit inside the box. A 0x85xx pair is ONE
    # half-width glyph, and the separator is the two-character backslash-n, so
    # neither can be counted as a plain byte.
    def _cols(line):
        i = c = 0
        while i < len(line):
            i += 2 if line[i] == 0x85 else 1
            c += 1
        return c

    for oldc, newc in SRVC_REWRITE:
        was = max(_cols(l) for l in oldc.replace(b"\\n", b"\n").split(b"\n"))
        for line in newc.split(b"\\n"):
            cols = _cols(line)
            # "never wider than it already was" rather than a flat cap: the
            # "no way to lead a unit" caption was ALREADY 40 columns against a
            # 38 cap before we touched it, so it is clipped in the shipping
            # build too. Not this batch's job to reword it, but it must not get
            # any worse. Pre-existing caption overflow is worth its own pass.
            limit = max(BOX, was)
            assert cols <= limit, "caption line is %d columns (was %d): %r" % (
                cols, was, line)
            flag = "  <- over the %d cap already" % BOX if cols > BOX else ""
            print("   %2d cols | %s%s"
                  % (cols, line.replace(b"\x85\x40", b".").decode("ascii", "replace"), flag))
    if write:
        f.seek(SRVC_LBA * SEC)
        f.write(bytes(srvc))

    print("\n--- renames applied ---")
    for old, _new in RENAME:
        print("   %-12s %d" % (old.decode(), stats.get(old, 0)))
    for ri, off, ob, nb, slot in stats.get("rewrites", []):
        print("   rewrite rec%-3d @%#08x  %d -> %d bytes (slot %d)" % (ri, off, ob, nb, slot))
    if stats.get("skipped"):
        print("\n   !! %d string(s) SKIPPED for want of room:" % len(stats["skipped"]))
        for s, old, need, slot in stats["skipped"][:10]:
            print("      @%#x %s needs %d, slot %d" % (s, old.decode(), need, slot))
    if not write:
        print("\n(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
