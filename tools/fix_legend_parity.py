# -*- coding: utf-8 -*-
"""DATA HELP spirit legend: pad odd non-final lines so all 5 rows are counted.

The panel counts rows two bytes per character (0.9.37) and misses a newline
that lands on an odd byte offset. The legend's L0 (51) and L3 (37) are odd, so
the counter saw 3 rows and clipped Va/Re/Wa/Fo and So/Al/Me/Co/An off the box.
One trailing ASCII space on each (invisible) makes every non-final line even and
all 17 spirits render. COMPDATA in place, +2 bytes in the slot.

Usage: fix_legend_parity.py <iso> [--write]
"""
import os, struct, sys
sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")
import banlz

SEC = 2048
COMP_LBA, COMP_NSEC = 1823000, 74
OFF = 0x722A0


def rowcount(data):
    i = 0; rows = 1
    while i < len(data):
        if data[i] == 0x0a:
            rows += 1; i += 1
        else:
            i += 2
    return rows


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(COMP_LBA * SEC)
    raw = bytearray(f.read(COMP_NSEC * SEC))
    live = [(h, d) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    hdr, data = live[0][0], bytearray(live[0][1])

    z = data.index(b"\x00", OFF)
    e = z
    while e < len(data) and data[e] == 0:
        e += 1
    slot = e - OFF - 1
    old = bytes(data[OFF:z])
    lines = old.split(b"\x0a")
    print("legend: %d lines, %d/%d bytes; counter now sees %d rows"
          % (len(lines), len(old), slot, rowcount(old)))

    fixed = []
    for i, ln in enumerate(lines):
        if i < len(lines) - 1 and len(ln) % 2 == 1:
            ln = ln + b"\x20"
            print("  L%d padded to even (%d)" % (i, len(ln)))
        fixed.append(ln)
    new = b"\x0a".join(fixed)
    assert rowcount(new) == len(lines), "still not %d rows" % len(lines)
    assert len(new) <= slot, "new %d > slot %d" % (len(new), slot)
    if new == old:
        print("already even - nothing to do"); f.close(); return
    print("counter now sees %d rows (all lines); +%d bytes" % (rowcount(new), len(new) - len(old)))

    data[OFF:OFF + slot + 1] = new + b"\x00" * (slot + 1 - len(new))
    blob = banlz.compress_record(bytes(data))
    if len(blob) > COMP_NSEC * SEC:
        blob = banlz.compress_record_optimal(bytes(data))
    assert hdr + len(blob) <= COMP_NSEC * SEC, "COMPDATA overflows"
    if not write:
        print("(dry run - pass --write)"); f.close(); return
    raw[hdr:hdr + len(blob)] = blob
    for x in range(hdr + len(blob), COMP_NSEC * SEC):
        raw[x] = 0
    f.seek(COMP_LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("COMPDATA written (%d bytes compressed)" % len(blob))


main()
