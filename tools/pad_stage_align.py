# -*- coding: utf-8 -*-
"""Restore STAGE's 16-byte record alignment.

REPORTED: the game crashes immediately after a scene ends - Ziene's
"your smile's so sexy" line in rec79, which is two rows from the end of that
record's script.

THE INVARIANT. Every STAGE record on the japanese disc has a length that is a
multiple of 16 - 205 of 205, no exceptions. In our build 151 of 205 are not,
because successive passes appended relocated strings to each record's tail and
stopped exactly at the last NUL. rec79 is 29938 bytes (0x74F2) against
japanese 29712 (0x7410).

WHY IT PLAUSIBLY CRASHES THERE. rec79's final string is the last line of the
scene - '$n / For real?' at 0x74e1 - and its terminator IS the record's last
byte. A PS2 DMA moves data in 16-byte quadwords, so reading a record whose
length is not a multiple of 16 reads past its end. That is harmless until the
bytes past the end are not mapped, which is why it shows up on one scene rather
than everywhere.

This restores the invariant rather than guessing at a specific fault: pad every
record with NUL bytes up to the next multiple of 16. That is safe by
construction -

  * no pointer changes: every pointer targets an offset BEFORE the old end;
  * no offset changes: bytes are only appended;
  * the record set is unchanged, and each record is re-checked against its slot;
  * NULs compress to almost nothing, so STAGE does not meaningfully grow -
    which matters, because STAGE may not grow much (see the changelog for the
    save-load hang).

Usage: pad_stage_align.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
ALIGN = 16


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    padded = grew = 0
    for ri, (hdr, data) in enumerate(live):
        d = bytes(data)
        rem = len(d) % ALIGN
        if rem == 0:
            continue
        need = ALIGN - rem
        new = d + b"\x00" * need
        assert len(new) % ALIGN == 0
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        room = nxt - hdr
        blob = banlz.compress_record(new)
        if len(blob) > room:
            blob = banlz.compress_record_optimal(new)
        if len(blob) > room:
            print("   rec%-4d SKIPPED: %d bytes needed, slot %d" % (ri, len(blob), room))
            continue
        old_blob_len = None
        if write:
            raw[hdr:hdr + len(blob)] = blob
            for x in range(hdr + len(blob), nxt):
                raw[x] = 0
        padded += 1
        grew += need
        if padded <= 8:
            print("   rec%-4d %d -> %d bytes (+%d), compressed %d in slot %d"
                  % (ri, len(d), len(new), need, len(blob), room))

    print("\n%d record(s) padded, %d bytes of NUL added in total" % (padded, grew))
    if write and padded:
        after = banlz.decompress_all(bytes(raw))
        live2 = [(h, x) for h, x in after if isinstance(h, int) and x is not None]
        assert [h for h, _ in live2] == [h for h, _ in live], "record set changed"
        bad = [i for i, (h, x) in enumerate(live2) if len(x) % ALIGN]
        assert not bad, "still unaligned: %s" % bad[:5]
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written; all %d records are now %d-byte aligned"
              % (len(live2), ALIGN))
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
