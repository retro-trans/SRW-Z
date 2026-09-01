# -*- coding: utf-8 -*-
"""Write the last japanese interface strings into COMPDATA.BN, in the image.

What is still japanese on screen after every earlier UI pass: the sortie-prep
caution popup ("no squad able to sortie has been formed"), the squad-list
headers, the spirit-command legend, the sort help, the search tabs.

It edits the COMPDATA record ALREADY IN THE IMAGE, not a fresh build from
extracted/DATA_COMPDATA.BN. That is deliberate. 0.8.81 repacked this string
pool and 0.8.90 repaired the 62 pointers the repack broke, so the shipped pool
no longer has the extract's layout - the same offsets there land on different
strings, and rebuilding from the extract would throw the 0.8.90 repair away.
The image is the source of truth for this record now.

For the same reason nothing is repacked here: apply_pool.py refuses COMPDATA
precisely because those 62 pointers sit on a pointer-table stride, and moving
the strings again would re-break them. Every string is written inside its own
NUL slot, so no offset moves and no pointer changes meaning.

Two encoding facts decide whether a line fits:

  * menu text goes through patch.encode(..., "menuhw"). Bytes 0x2E-0x3D are
    CONTROL CODES to the menu reader, so digits and '.' take the private
    half-width codes - two bytes each, not one. That is what put twelve of
    these lines over budget on the first pass.
  * button markup is NOT menu text. The original stores <-5> as plain ASCII
    (3c 2d 35 3e); the renderer consumes the token before the font path ever
    sees it. Encoding it would cost 6 bytes instead of 4 and change what the
    game draws, so markup passes through verbatim and only the words around it
    are encoded.

Usage: apply_compdata_ui.py <iso> [--dry-run]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import banlz
import compdata_ui_left
import pool
from patch import encode

SECTOR = 2048
NAME = "COMPDATA.BN;1"

NL = chr(10)
# Strings the menu encoder must NOT touch. compdata_ui_left runs every entry
# through patch.encode(..., "menuhw"), which maps '.' to a private half-width
# cell - right for menu labels, wrong for battle-caption prose: it turned
# "this...!" into three extra bytes and three glyphs the caption path does not
# draw. These are replaced as raw cp932 inside their own slot instead.
#
# 2026-08-31: Brai -> Burai. The Getter Robo G emperor 大帝ブライ is spelled
# "Burai" by every English source (Getter Robo Wiki, Villains Wiki, Go Nagai
# Wiki); "Brai" appeared nowhere.
RAW = {
    0x061a18: ("W-What is this...! That I," + NL + "Brai, should be defeated!",
               "W-What is this...! That I," + NL + "Burai, should be defeated!"),
    0x061a50: ("L-Lord Brai, forgive me!", "L-Lord Burai, forgive me!"),
}


RAW_FILE = os.path.join(os.path.dirname(HERE), "analysis", "compdata_raw.json")


def raw_table():
    """RAW plus anything rewrap_help.py generated, as {offset: (old, new)}."""
    t = dict(RAW)
    if os.path.exists(RAW_FILE):
        import io
        import json
        for k, v in json.load(io.open(RAW_FILE, encoding="utf-8")).items():
            t[int(k, 16)] = (v[0], v[1])
    return t


def apply_raw(d, guard):
    """Exact-byte replacements inside a slot. Returns (done, complaints)."""
    done, bad = 0, []
    table = raw_table()
    for off in sorted(table):
        old, new = (s.encode("cp932") for s in table[off])
        z = d.index(bytes([0]), off)
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        cur = bytes(d[off:z])
        if cur == new:
            continue
        if cur != old:
            bad.append((off, "on-disc text is not the expected original",
                        cur.decode("cp932", "replace")))
            continue
        if any(off <= g < off + len(new) + 1 for g in guard):
            bad.append((off, "a pointer targets this slot", ""))
            continue
        if len(new) >= k - off:
            bad.append((off, "needs %d bytes, slot holds %d" % (len(new), k - off), ""))
            continue
        d[off:k] = new + bytes(k - off - len(new))
        done += 1
    return done, bad
# COMPDATA lives in /DMY/DMY.BIN's padding at LBA 1823000; the encyclopedia's
# keyword archive starts at 1823200. That gap - not the current extent - is the
# real ceiling on how far this record may grow.
ROOM = 1823200 - 1823000


def table_entry(head):
    """The game's own file table wins over ISO9660: the path with DOUBLED
    backslashes, then [u32 LBA][u32 sectors] at name+0x20. libcdvd reads
    this, not the directory record - but both are kept in step below."""
    n = head.find(NAME.encode())
    while n >= 0:
        if head[n - 8:n] == (chr(92) * 2 + "DATA" + chr(92) * 2).encode():
            return n
        n = head.find(NAME.encode(), n + 1)
    raise SystemExit("file-table entry for COMPDATA.BN not found")


def main():
    iso = sys.argv[1]
    dry = "--dry-run" in sys.argv

    f = open(iso, "rb")
    head = f.read(4 * 1024 * 1024)
    n = table_entry(head)
    lba, sectors = struct.unpack_from("<II", head, n + 0x20)
    f.seek(lba * SECTOR)
    # Read a generous window, not exactly the recorded extent. The extent is
    # rewritten to what the record NEEDS on every pass, so reading exactly it
    # would make each run's headroom the previous run's output - a guard that
    # tightens itself until a legitimate edit is refused.
    cur = f.read(max(sectors, ROOM) * SECTOR)
    f.close()

    d, _ = banlz.decompress_record(cur, 0)
    d = bytearray(d)
    # the 62 pointers 0.8.90 repaired: some aim at a string's NUL padding on
    # purpose, so writing through that padding would re-break them
    ent = pool.entries(d)
    guard = set()
    for x in pool.stray_pointers_on_a_stride(d, [s for s, _t, _k in ent]):
        guard.add(x[1] if isinstance(x, (tuple, list)) else x)
    written, over = compdata_ui_left.apply(d, encode, guard)
    if over:
        print("WILL NOT FIT: %d string(s)" % len(over))
        for off_s, need, slot, text in over:
            print("   %s needs %3d, slot %3d  %r" % (off_s, need, slot, text))
        return 1
    raw_done, raw_bad = apply_raw(d, guard)
    for off, why, have in raw_bad:
        print("RAW %#08x skipped: %s" % (off, why))
        if have:
            print("   have %r" % have)
    print("%d strings written in place (%d raw), no offset moved"
          % (written + raw_done, raw_done))
    if dry:
        return 0

    blob = banlz.compress_record(bytes(d))
    back, _ = banlz.decompress_record(blob, 0)
    if back != bytes(d):
        raise SystemExit("banlz roundtrip failed - not writing")
    need = (len(blob) + SECTOR - 1) // SECTOR
    if need > ROOM:
        raise SystemExit("recompressed COMPDATA needs %d sectors; only %d are "
                         "free before the next region at LBA %d"
                         % (need, ROOM, 1823200))
    print("compressed %d bytes (%d sectors; %d free before LBA %d)"
          % (len(blob), need, ROOM, 1823200))

    iso_f = open(iso, "r+b")
    iso_f.seek(lba * SECTOR)
    iso_f.write(blob + bytes(sectors * SECTOR - len(blob)))
    # keep both descriptions of the size honest
    iso_f.seek(n + 0x24)
    iso_f.write(struct.pack("<I", need))
    p = head.find(NAME.encode())
    rec = p - 33
    if struct.unpack_from("<I", head, rec + 2)[0] == lba:
        iso_f.seek(rec + 10)
        iso_f.write(struct.pack("<I", len(blob)))
        iso_f.seek(rec + 14)
        iso_f.write(struct.pack(">I", len(blob)))
    iso_f.close()
    print("COMPDATA.BN rewritten at LBA %d" % lba)
    return 0


if __name__ == "__main__":
    sys.exit(main())
