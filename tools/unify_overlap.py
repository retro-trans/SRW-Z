# -*- coding: utf-8 -*-
"""One English name for 相克界: "Overlap".

The keyword was rendered twelve different ways across the script - Overlap,
Dimensional Rift, Conflict Field, Conflict Zone, the Rift, the barrier, the
dimensional barrier, the Aether Barrier, the Barrier, Interference, Cross-Realm,
Mutual Exclusion World, "the walls between worlds" - so the same glossary entry
was called something new almost every time it came up. The popup title (set in
fix_popup_titles.py) is "Overlap", so the prose follows it.

Bodies are given flat; the script wraps them with the placeholder-aware wrapper
and refuses anything that does not fit 3 lines x 34 columns or its byte slot.

Usage: unify_overlap.py <iso> [--dry-run]
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from fix_placeholder_wrap import ecols, wrap
from rewrap_dialogue import LBA, SECTOR, SIZE, WIDTH, MAXLINES

Q1, Q2 = u"\u300c", u"\u300d"
NEW = {
 (25, 88240):  (u"Renton",    Q1+u"Even at war, the Overlap means only some areas see battle."+Q2),
 (25, 96992):  (u"Renton",    Q1+u"The Overlap is thin here, so ZAFT built their stronghold base..."+Q2),
 (25, 97344):  (u"$n",        Q1+u"But if the Overlap's thin here... that means \u300aTrapar\u300b's thick around here."+Q2),
 (26, 45968):  (u"Julie",     Q1+u"Then they're aliens too...! And they broke through the Overlap to reach Earth!?"+Q2),
 (26, 60816):  (u"Heizaemon", Q1+u"Hmm... thanks to the Overlap, watching space from Earth's gotten harder..."+Q2),
 (26, 75120):  (u"$n",        Q1+u"Broke through the Overlap, huh? Not bad at all."+Q2),
 (29, 45664):  (u"Holland",   Q1+u"Maybe the Overlap's thin, but good waves always draw a fight."+Q2),
 (31, 71472):  (u"Quattro",   Q1+u"You've had it rough too. Crossing the Overlap to reach Earth can't have been easy."+Q2),
 (32, 47088):  (u"Durandal",  Q1+u"The Overlap's thin in that area, so please be careful."+Q2),
 (40, 54640):  (u"Gain",      Q1+u"The Overlap's thin over Siberia. Means Trapar's thick here. Conditions check out."+Q2),
 (50, 91184):  (u"Guin",      Q1+u"Crossing the Overlap to do it... he spares no effort for his goals."+Q2),
 (53, 82048):  (u"Ghingnham", Q1+u"A hole in the Overlap, you say?"+Q2),
 (53, 82192):  (u"Suesson",   Q1+u"It tore through the Overlap, and a huge hole opened up there."+Q2),
 (58, 54304):  (u"Roberto",   Q1+u"Coming from a universe split off by the Overlap, running the Fed's gauntlet all the way..."+Q2),
 (62, 47792):  (u"Mizuki",    Q1+u"Right. The Overlap's thin here, so the town evacuated."+Q2),
 (62, 47888):  (u"Toshiya",   Q1+u"A thin Overlap means aliens descend more easily here."+Q2),
 (66, 95344):  (u"Uchuta",    Q1+u"But how do they even get to space? With the Overlap out there, it's not that simple."+Q2),
 (80, 56416):  (u"Yzak",      Q1+u"We crossed the Overlap to reach ground! Not going home empty!"+Q2),
 (85, 53696):  (u"Garrod",    Q1+u"Not bad...! You made it through the Overlap!"+Q2),
 (95, 76752):  (u"Pala",      Q1+u"Huh... breaking the Overlap for space - must be important."+Q2),
 (102, 37184): (u"Leben",     Q1+u"With the Overlap, travel is risky. How do you plan to manage it?"+Q2),
 (104, 61536): (u"Bradman",   Q1+u"Damn you, aliens! The Overlap thins, and you attack at once!"+Q2),
 (104, 91952): (u"Daisuke",   Q1+u"The Overlap is thinning worldwide, Trapar rising."+Q2),
 (104, 92032): (u"Julie",     Q1+u"This is bad.. The Overlap kept space travel limited until now."+Q2),
 (105, 26896): (u"Banjo",     Q1+u"As the Overlap weakens, alien attacks will worsen. Be ready for that too."+Q2),
 (107, 116848):(u"Heizaemon", Q1+u"With the Overlap thin, aliens press on.."+Q2),
 (109, 103760):(u"Ghingnham", Q1+u"So it's you! You who broke through the Overlap and punched the Moon repeatedly!"+Q2),
 (154, 30736): (u"Durandal",  Q1+u"Glad you came. Even with the Overlap thin here, the trip from Orb must've been tiring."+Q2),
}


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    built = {}
    for key, (name, flat) in sorted(NEW.items()):
        lines = wrap(flat)
        assert len(lines) <= MAXLINES, "%s: %d lines %s" % (key, len(lines), lines)
        for l in lines:
            assert ecols(l) <= WIDTH, "%s: %d cols %r" % (key, ecols(l), l)
        built[key] = u"\n".join([name] + lines)
    print("all %d rewrites fit %dx%d" % (len(built), MAXLINES, WIDTH))

    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    recs = {}
    for (idx, off), text in sorted(built.items()):
        b = recs.setdefault(idx, bytearray(items[idx][1]))
        e = off
        while b[e] != 0:
            e += 1
        k = e
        while k < len(b) and b[k] == 0:
            k += 1
        nb = text.encode("cp932")
        assert len(nb) < k - off, "rec %d @%d: %d bytes > slot %d" % (idx, off, len(nb), k - off)
        b[off:k] = nb + b"\x00" * (k - off - len(nb))
    print("%d strings in %d records" % (len(built), len(recs)))
    if dry:
        return

    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, [(i, bytes(b)) for i, b in recs.items()]))
    pool.close(); pool.join()
    for idx, b in recs.items():
        hdr = items[idx][0]
        blob = packed[idx]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % idx
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    changed = sorted(o for o in before if check[o] != before[o])
    assert changed == sorted(items[i][0] for i in recs), "unexpected records changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done - %d records changed, and only those" % len(changed))


if __name__ == "__main__":
    main()
