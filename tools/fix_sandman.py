# -*- coding: utf-8 -*-
u"""Fix the サンドマン (Sandman) mistranslation, plus three screenshot lines.

REPORTED: "Eiji keeps calling other characters Eiji." The name plate is right -
Eiji IS the speaker - but the machine translation kept replacing the person he
ADDRESSES, サンドマン (Sandman), with the speaker's own name. The same error hits
Raven's lines (Sandman -> "Raven") and Leele's scenes (Sandman -> "Leele"), and
デュークフリード (Duke Fleed) became "Eiji Fleed".

The name is unambiguous: name_source.json maps サンドマン -> Sandman, and the
COMPDATA character records already say Sandman (and Sandman B/W/G for his mechs).

Each correction is a FULL replacement field (speaker + body), wrapped by hand to
stay inside the box, applied in place inside its own slot. Nothing moves.

NOT touched - flagged for separate review: rec131's rows, whose English bears no
relation to the Japanese (a scramble, not a name swap), and two pun lines
(rec120/rec131 "仏の顔もサンドマン") that read fine in English without the name.

Usage: fix_sandman.py <iso> [--write]
"""
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
OQ, CQ = u"「", u"」"       # 「 」

# (rec, offset, new field text). Offsets from the 0.9.38 image.
FIX = [
    # --- screenshot lines ---
    (70, 0x52bd, u"Emma\n「When he heard that name,\nhe... his face changed color.」"),
    (56, 0x9020, u"Athena\n「I must report this to\nCaptain Olson...!」"),
    (57, 0xc620, u"Kamille\n「End the sorrow」"),

    # --- Duke Fleed (デュークフリード), not "Eiji Fleed" ---
    (30, 0xdda0, u"Eiji\n「I trust you, Duke Fleed...!\nAnd you too, Hikaru!」"),
    (69, 0x1cb90, u"Eiji\n「Don't say another word, Duke\nFleed! Humanity can't survive on\nyour naive ideals!」"),
    (98, 0x15500, u"Eiji\n「Duke Fleed...! We're not gonna\ndiscriminate against you for being\nan alien!」"),
    (47, 0xf2e0, u"Koji\n「Sure, your case may differ from\nDuke Fleed's, but you touched\nhis honest heart...」"),

    # --- Sandman as "Eiji" ---
    (7, 0x11a50, u"Eiji\n「This is Sandman...!」"),
    (8, 0x3c40, u"Eiji\n「Tch... what's with Sandman...\nGoing awfully easy on her.」"),
    (8, 0x4840, u"Eiji\n「Me...? My hunch is that\nSandman's hiding something about\nAyaka after all.」"),
    (8, 0x4a00, u"Eiji\n「Why are you in a place like\nthis? Does Sandman know?」"),
    (10, 0xdff0, u"Eiji\n「Sandman! Great, cool entrance\nand all, but what are we supposed\nto actually do?!」"),
    (26, 0xdaf0, u"Eiji\n「Still, that Sandman... Japan is\nsealed, yet the combine order\nalways comes on time.」"),
    (48, 0x18e40, u"Eiji\n「Sandman's probably the same. He\ntold us to go with the Minerva\ntoo.」"),
    (64, 0x5780, u"Eiji\n「What's going on, Sandman!? Is\nthat blond guy you!?」"),
    (64, 0x6180, u"Eiji\n「So this Hyuugi guy blamed\nSandman for it...」"),
    (64, 0x8350, u"Eiji\n「Sandman...」"),
    (64, 0x91d0, u"Eiji\n「Not like you, Sandman. Making a\nface like that.」"),
    (65, 0xa4a0, u"Eiji\n「Come on, Zeravire! For Sandman,\nwe're your foes!」"),
    (65, 0xb800, u"Eiji\n「Good timing, Sandman. A widower\nfor centuries-maybe it's time to\nremarry?」"),
    (133, 0xcd70, u"Eiji\n「No way, Sandman...! He got\ncaught in the transformation!?」"),
    (133, 0xcfa0, u"Eiji\n「Touga! Then we stop Goma and\ndrag Sandman out of there\nourselves!」"),
    (133, 0xdc20, u"Eiji\n「Don't screw around, Sandman! You\nowe me a mountain of debts!」"),
    (133, 0xe0a0, u"Eiji\n「Let's do this, Sandman!」"),

    # --- Sandman as "Raven" (レイヴン is a different, real character) ---
    (7, 0xcda0, u"Eiji\n「Klein Sandman... so Ayaka is\nwith that guy...」"),
    (7, 0x10b90, u"Raven\n「Now, Klein Sandman, one of\ntonight's hosts, will offer his\ngreetings to you all.」"),
    (7, 0x11a10, u"Raven\n「This is Klein Sandman, master\nof this castle.」"),
    (7, 0x12620, u"Raven\n「Sandman surely has his deep\nreasons. We need only trust in\nhim.」"),
    (26, 0x13ac0, u"Raven\n「...Sandman.」"),
    (26, 0x13c80, u"Raven\n「Sandman...」"),
    (26, 0x13ca0, u"Chuille\n「Lord Sandman's aesthetic\nagain...?」"),
    (64, 0x7b60, u"Raven\n「Sandman, I've shown in the\n$c members.」"),
    (64, 0x9400, u"Raven\n「Sandman...」"),
    (65, 0xb5a0, u"Raven\n「Sandman...」"),
    (105, 0x68f0, u"Raven\n「Sandman...」"),
    (105, 0x6a10, u"Raven\n「Sandman! Pull yourself\ntogether!」"),
    (107, 0x1f180, u"Raven\n「Sandman.」"),
    (107, 0x20b10, u"Faye\n「But Sandman changed his mind. He\nchose you, a G Factor holder,\nas pilot.」"),
    (133, 0xddd0, u"Mizuki\n「Raven! Call out to him too!\nYou're the only one who can wake\nSandman up!」"),
    (133, 0xde40, u"Raven\n「Sandman! No, Zieg! We all\nneed you!」"),
    (154, 0x7c70, u"Raven\n「Sandman, perhaps we should call\nback at least the Gran Knights,\nafter all...」"),
    (154, 0x7da0, u"Raven\n「But Sandman…」"),
    (154, 0x7f80, u"Raven\n(He knows Sandman's past...? Who\nis this man...)"),

    # --- Sandman as "Leele" (リィル), or the speaker's own name ---
    (9, 0x9da0, u"Mizuki\n(That girl Leele... Sandman said\nshe's lost her memory, but...)"),
    (31, 0x16120, u"Luna\n「No way, Mizuki! Do that to Leele\nand Sandman won't stay quiet!」"),
    (48, 0x10720, u"Umee\n「We've got word in from\nSandman. He says they'll wrap\nup soon too.」"),
    (52, 0xd840, u"Mizuki\n(Sandman... he must know about\nTouga and Eiji's situation now...)"),
    (65, 0xa080, u"$n\n「Maybe that's why Sandman had\nLeele wait in a separate room...」"),
    (65, 0xa0d0, u"Gengoro\n「There's the Leele matter\ntoo. King Beal heads to\nSandman's villa.」"),
    (65, 0xab90, u"Koji\n「Please tell us, Sandman. About\nLeele and Zeravire's connection.」"),
    (65, 0xae40, u"Uchuta\n「So is Leele immortal like\nyou, Sandman? Is she really\nhundreds of years old too?」"),
    (65, 0xc940, u"Touga\n「And, Leele... Sandman is your\nfather.」"),
    (68, 0x8830, u"Touga\n「For the sake of Leele, waiting\nback with Sandman!」"),
    (102, 0xdda0, u"Jun\n「Leele is... Sandman's\ndaughter...!?」"),
    (102, 0xe050, u"Luna\n「That's why Sandman kept that\nstory from Leele...」"),
    (104, 0x10ca0, u"Touga\n「This is... the only thing I can\ndo now for Leele and Sandman!」"),
    (120, 0x108e0, u"Kazami\n「Sandman! You dare get in my way\ntoo?!」"),
    (154, 0x4240, u"Eiji\n「Don't make that face, Leele.\nNo matter what Japan's government\nsays, Sandman's fine.」"),

    # --- synopsis (rec0): one Sandman reference, keep the correct Eiji ---
    (0, 0x8ef0, u" The party sought out Eiji, but his resolve was firm. As\nthe alien alliance attacked, Toshiya and others sortied,\nbut Gaizok targeted the townsfolk. Terar, moved by\nToshiya's courage, responded in kind. Against a new\nZelabia, the reunited Grand Knights fought but were\noutmatched. Sandman granted them a new power, the Super\nHeavy Sword. He rejoiced in their growth, yet his past\nwounds ached."),
]

# rec131 - English unrelated to the Japanese (scramble), needs full review.
FLAG = [(131, 0x19f80), (131, 0x19fa0), (131, 0x1a100),
        (131, 0x1a230), (131, 0x1a260), (131, 0x1a380)]


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


def cols(line):
    return sum(2 if ord(c) > 0x7F else 1 for c in line)


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    touched, over = {}, []
    for ri, off, new in FIX:
        d = live[ri][1]
        cur, slot = slot_at(d, off)
        nb = new.encode("cp932")
        if cur is None:
            print("  rec%-3d @%#06x: NO STRING (offset drift?)" % (ri, off))
            continue
        if nb == cur:
            continue
        if len(nb) > slot:
            over.append((ri, off, len(nb), slot, new))
            continue
        widest = max((cols(l) for l in new.split(u"\n")[1:]), default=0)
        if widest > 34 and ri != 0:
            over.append((ri, off, len(nb), slot, new + u"  [%dcols]" % widest))
            continue
        d[off:off + slot + 1] = nb + b"\x00" * (slot + 1 - len(nb))
        touched[ri] = d

    print("rows corrected      : %d" % (len(FIX) - len(over)))
    print("rows OVER BUDGET    : %d" % len(over))
    for ri, off, need, slot, new in over:
        print("   rec%-3d @%#06x needs %d, slot %d: %s"
              % (ri, off, need, slot, new.replace(u"\n", u" / ")))
    print("\nflagged for separate review (English unrelated to Japanese): %d rows in rec131"
          % len(FLAG))

    if not touched or not write:
        if touched:
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
        assert len(blob) <= nxt - hdr, "rec%d over slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("\nSTAGE written (%d records)" % len(touched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
