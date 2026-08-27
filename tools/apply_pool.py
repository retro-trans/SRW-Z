# -*- coding: utf-8 -*-
"""Repack the COMPDATA string pool and splice it back into an image.

Lifts the per-name byte budget: names are no longer confined to the slot they
were shipped in. See tools/pool.py for how the pointer table was found.

  apply_pool.py <iso> [--set OFFSET=TEXT ...] [--from FILE.json] [--write]

FILE.json is {"0x66f48": "Musou Sword", ...} - keys are ORIGINAL pool offsets.

RUN THIS LAST in the COMPDATA pipeline. patch_compdata.py rebuilds the record
from extracted/DATA_COMPDATA.BN and keys 290 UI-string edits (compdata_ui_en.py
and _b.py) by pool offset, so those offsets assume the SHIPPED layout. Repacking
moves every string; re-running patch_compdata afterwards silently rebuilds an
un-repacked record, and re-running this on an already-repacked image fails loudly
because the original offsets are no longer string starts. Order:

    patch_compdata.py  ->  ... other COMPDATA passes ...  ->  apply_pool.py

The old->new offset map is written to analysis/pool_remap.json on every --write,
so an offset-keyed pass can be re-pointed instead of re-run from scratch.

Text is written with the MENU encoding, not plain cp932: these strings are drawn
by the 0x13A290 reader, where byte values 0x2E-0x3D ('.' and '0'-'9') are
CONTROL CODES. Encoding "75mm Autocannon" as ASCII would feed the renderer two
commands instead of two digits. That is why the names already in the image read
'７５mm AutoGun' and 'S．３D MugenFst'.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import pool
from patch import encode

SEC = 2048
LBA, NSEC = 1823000, 74


def load_rec(iso):
    f = open(iso, "rb")
    f.seek(LBA * SEC)
    raw = f.read(NSEC * SEC)
    f.close()
    items = banlz.decompress_all(raw)
    if not items:
        raise SystemExit("no banlz record at LBA %d in %s" % (LBA, iso))
    return bytes(items[0][1])


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    repl = {}
    if "--from" in sys.argv:
        src = json.load(open(sys.argv[sys.argv.index("--from") + 1], encoding="utf-8"))
        for k, v in src.items():
            repl[int(k, 0)] = encode(v, "menu")
    for i, a in enumerate(sys.argv):
        if a == "--set":
            k, _, v = sys.argv[i + 1].partition("=")
            repl[int(k, 0)] = encode(v, "menu")

    rec = load_rec(iso)
    ent = pool.entries(rec)
    by = {a: t for a, t, s in ent}
    print("pool entries: %d" % len(ent))
    for off, text in sorted(repl.items()):
        cur = by.get(off)
        if cur is None:
            raise SystemExit(
                "offset %#x is not a string start. This usually means the "
                "pool in %s has ALREADY been repacked, so the original "
                "offsets no longer exist. Rebuild COMPDATA with "
                "patch_compdata.py first, then run this pass last."
                % (off, iso))
        print("  %#08x  %-28r -> %r" % (off, cur.decode("cp932", "ignore"),
                                        text.decode("cp932", "ignore")))
    new, end, newoff = pool.repack(rec, repl)
    print("pool ends %#x, free %d bytes" % (end, pool.POOL_HI - end))
    if not write:
        print("\n(dry run - pass --write to apply)")
        return

    # The fast coder first: repacking leaves ~22KB of NULs at the tail, which
    # compresses to almost nothing, so it usually fits with room to spare and
    # saves ~25 minutes over the optimal parser. Fall back only if it does not.
    blob = banlz.compress_record(new)
    print("fast coder: %d bytes (slot %d)" % (len(blob), NSEC * SEC))
    if len(blob) > NSEC * SEC:
        print("does not fit - running the optimal parser (slow)")
        blob = banlz.compress_record_optimal(new)
        print("optimal coder: %d bytes" % len(blob))
    if len(blob) > NSEC * SEC:
        raise SystemExit("REFUSED: recompressed %d > slot %d" % (len(blob), NSEC * SEC))
    out = bytearray(NSEC * SEC)
    out[:len(blob)] = blob
    f = open(iso, "r+b")
    f.seek(LBA * SEC)
    f.write(bytes(out))
    f.close()
    chk = load_rec(iso)
    assert chk == new, "readback mismatch"
    json.dump({"%#x" % a: "%#x" % b for a, b in newoff.items()},
              open("analysis/pool_remap.json", "w"), indent=0)
    print("written and verified (%d compressed bytes)" % len(blob))
    print("old->new offset map: analysis/pool_remap.json (%d entries)" % len(newoff))


if __name__ == "__main__":
    main()
