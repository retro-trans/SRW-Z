# -*- coding: utf-8 -*-
"""Un-abbreviate the generic-soldier speaker names in STAGE dialogue.

"Chiram Sldr" / "Cherudim Sldr" come from compdata_en.py's SHORT table,
which exists because the UNIT-list name cell is tiny.  The dialogue name
plate has no such limit - the budget there is the whole
"Name\\n\\u300ctext\\u300d" string against its NUL slot, and 22 of the 34
instances already had room.  The other 12 needed exactly 3 bytes, so
their line is tightened by a word rather than left inconsistent.

Splicing follows the safe pattern (see the 0.8.45 changelog): decompress
from the CURRENT iso, edit, compress_record_optimal into the existing
slot, and verify every other record is byte-identical before writing.

Usage: patch_speaker_names.py <iso> [--dry-run]
"""
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")

import banlz

LBA, SIZE, SECTOR = 1651029, 3910128, 2048
NAMES = {b"Chiram Sldr": b"Chiram Soldier",
         b"Cherudim Sldr": b"Cherudim Soldier",
         b"Alliance Sldr": b"Alliance Soldier",
         b"Gaizock Sldr": b"Gaizock Soldier",
         b"Emaan Sldr": b"Emaan Soldier",
         b"Elder Sldr": b"Elder Soldier",
         b"Titans Sldr": b"Titans Soldier",
         b"Fed. Sldr": b"Fed. Soldier",
         b"DC Sldr": b"DC Soldier"}

Q0, Q1 = "\u300c", "\u300d"

# (record, offset): the tightened line, name already expanded.  Each of
# these was exactly 3 bytes short of fitting the longer name.
TIGHT = {
    (23, 0x5c50): "Chiram Soldier\n" + Q0 + "Fine! All units, attack!" + Q1,
    (23, 0x7e90): "Chiram Soldier\n" + Q0 + "It's from that machine..." + Q1,
    (23, 0x7ec1): "Chiram Soldier\n" + Q0 + "Right... I'll talk. Rest of you,\nstand by." + Q1,
    (23, 0x7f22): "Chiram Soldier\n" + Q0 + "That was a warning. Interfere\nagain and I won't hold back." + Q1,
    (23, 0x7f83): "Chiram Soldier\n" + Q0 + "What the!?" + Q1,
    (28, 0x1d30b): "Chiram Soldier\n" + Q0 + "Yes, Lt. Henry. We're getting a\nclear Singularity signal from\nthis market..." + Q1,
    (28, 0x1d36b): "Chiram Soldier\n" + Q0 + "Sensor's reacting to her." + Q1,
    (28, 0x1d41f): "Chiram Soldier\n" + Q0 + "L-Lt. Henry! We're picking up a\nstronger Singularity signal\nfrom this man!" + Q1,
    (28, 0x1d4a0): "Chiram Soldier\n" + Q0 + "Sensors are reacting to him." + Q1,
    (41, 0x105ac): "Chiram Soldier\n" + Q0 + "Capture those too and it\nstrengthens Chiram...! Let's\nmove!" + Q1,
    (42, 0x99d0): "Chiram Soldier\n" + Q0 + "Not as strong as those two, but\nsmall anomalies like them seem to\nbe fairly common here." + Q1,
    (42, 0x9a40): "Chiram Soldier\n" + Q0 + "Capture those too, and it\nstrengthens Chiram...! Move!" + Q1,
    (6, 0xb3a0): "Alliance Soldier\n" + Q0 + "Don't move! One wrong move and\nwe shoot!" + Q1,
    (6, 0xb5c0): "Alliance Soldier\n" + Q0 + "Yes, sir." + Q1,
    (6, 0xea86): "Alliance Soldier\n" + Q0 + "We're taking you deserters in!\nDisarm and step out!" + Q1,
    (34, 0x126f7): "DC Soldier\n" + Q0 + "And... sorry for calling you\nbackwater savages" + Q1,
    (53, 0xd490): "Gaizock Soldier\n" + Q0 + "Don't struggle, humans! Into\nthe container!" + Q1,
    (79, 0x4c70): "Emaan Soldier\n" + Q0 + "You're $c." + Q1,
    (106, 0x7a40): "Titans Soldier\n" + Q0 + "Contact! Fast ship nearing\nthis sector!" + Q1,
}


def cols(line):
    return sum(2 if ord(c) > 0x7f else 1 for c in line)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    hdrs = sorted(o for o, d in items if d is not None)
    edited, renamed, tightened = {}, 0, 0

    for idx, (hdr, dec) in enumerate(items):
        if dec is None:
            continue
        d = bytearray(dec)
        touched = False
        # 1) the hand-tightened lines
        for (rec, off), text in TIGHT.items():
            if rec != idx:
                continue
            e = d.index(b"\x00", off)
            k = e
            while d[k] == 0:
                k += 1
            slot, nb = k - off, text.encode("cp932")
            assert len(nb) < slot, ("tight", rec, hex(off), len(nb), slot)
            for ln in text.split("\n")[1:]:
                assert cols(ln) <= 34, (rec, hex(off), ln)
            d[off:off + slot] = nb + b"\x00" * (slot - len(nb))
            tightened += 1
            touched = True
        # 2) every remaining instance that already has room
        for old, new in NAMES.items():
            pos = 0
            while True:
                j = bytes(d).find(old, pos)
                if j < 0:
                    break
                pos = j + 1
                s = j
                while s > 0 and d[s - 1] != 0:
                    s -= 1
                e = d.index(b"\x00", j)
                k = e
                while d[k] == 0:
                    k += 1
                grow = len(new) - len(old)
                if (e - s) + grow < (k - s):
                    line = bytes(d[s:e]).replace(old, new)
                    d[s:s + (k - s)] = line + b"\x00" * ((k - s) - len(line))
                    renamed += 1
                    touched = True
                    pos = s + len(line)
        if touched:
            edited[idx] = (hdr, bytes(d))

    print("records touched: %s" % sorted(edited))
    print("names expanded in place: %d, lines tightened: %d"
          % (renamed, tightened))
    still = sum(bytes(d).count(b"Sldr") for _h, d in edited.values())
    print("remaining 'Sldr' inside the touched records: %d" % still)
    if dry:
        f.close()
        return

    out = bytearray(raw)
    for idx, (hdr, plain) in sorted(edited.items()):
        nxt = min([o for o in hdrs if o > hdr] or [SIZE])
        slot = nxt - hdr
        blob = banlz.compress_record_optimal(plain)
        assert len(blob) <= slot, (idx, len(blob), slot)
        out[hdr:nxt] = blob + b"\x00" * (slot - len(blob))
        print("  spliced rec%-3d %6d into %6d-byte slot" % (idx, len(blob), slot))
    after = {o: bytes(x) for o, x in banlz.decompress_all(bytes(out))
             if x is not None}
    assert not [o for o in before if o not in after], "a record vanished"
    changed = sorted(o for o in before if after[o] != before[o])
    want = sorted(h for h, _p in edited.values())
    assert changed == want, (changed, want)
    f.seek(LBA * SECTOR)
    f.write(bytes(out))
    f.close()
    print("done - only the %d intended records changed" % len(want))


if __name__ == "__main__":
    main()
