# -*- coding: utf-8 -*-
u"""Diagnostic: what does each speech delimiter do in the BACK LOG?

The dialogue box puts field line 1 on a coloured name plate, so the delimiter
is invisible work there. The Back Log has no plate - a previous PINE session
established it "draws the RAW record strings (never setText-converted)"
(tools/patch_backlog.py) - so whatever separates a name from speech there has
to come out of the string itself.

corridor_polish.py records the engine behaviour we are testing against:

    "..." quotes -> 「...」 (also turns the speaker name blue - engine behavior)

If that holds in the Back Log too, only 「」 colours the name and neither ASCII
quotes nor bare text will. This puts all three side by side, on three
CONSECUTIVE lines of the Titans corridor scene (rec1), so one backlog screen
answers it:

    Emma      -> BARE          no delimiter at all
    Kacricon  -> "ASCII"       what most of the script uses where 「」 was dropped
    Jerid     -> 「KAGI」        unchanged, the control

Read the backlog and compare: which speaker names are blue, and where does the
name visibly end?

Reversible with --revert.

Usage: diag_corridor_quotes.py <iso> [--write] [--revert]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
REC = 1

KO = bytes([0x81, 0x75])          # 「  built without escapes
KC = bytes([0x81, 0x76])          # 」
NL = bytes([0x0A])
Q = b'"'

CASES = [
    # (offset, original, variant, label)
    (0x08be0,
     b"Emma" + NL + KO + b"What are you two doing?" + KC,
     b"Emma" + NL + b"What are you two doing?",
     "BARE      (no delimiter)"),
    (0x08c10,
     b"Kacricon" + NL + KO + b"Tch... here comes trouble." + KC,
     b"Kacricon" + NL + Q + b"Tch... here comes trouble." + Q,
     'ASCII     ("...")'),
    # Jerid at 0x08c40 is left alone on purpose - it is the control.
]


def slot_at(b, off):
    z = b.find(b"\x00", off)
    if z < 0:
        return None, None
    e = z
    while e < len(b) and b[e] == 0:
        e += 1
    return bytes(b[off:z]), e - off - 1


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    revert = "--revert" in sys.argv

    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    hdr, data = live[REC][0], bytearray(live[REC][1])

    changed = 0
    for off, orig, variant, label in CASES:
        old, new = (variant, orig) if revert else (orig, variant)
        cur, slot = slot_at(data, off)
        if cur == new:
            print("  @%#07x already %s" % (off, "reverted" if revert else "set"))
            continue
        assert cur == old, ("@%#07x unexpected content\n   have %r\n   want %r"
                            % (off, cur, old))
        assert len(new) <= slot, "@%#07x needs %d, slot %d" % (off, len(new), slot)
        data[off:off + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
        changed += 1
        print("  @%#07x %-26s %d -> %d bytes" % (off, label, len(old), len(new)))
        print("      %r" % new)

    if not changed:
        print("nothing to do")
        f.close()
        return 0

    ctrl, _ = slot_at(data, 0x08c40)
    print("\n  control (unchanged): %r" % ctrl)

    nxt = min([h for h in heads if h > hdr] or [len(raw)])
    blob = banlz.compress_record(bytes(data))
    if len(blob) > nxt - hdr:
        blob = banlz.compress_record_optimal(bytes(data))
    assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % REC
    if write:
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
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
