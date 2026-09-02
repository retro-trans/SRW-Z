# -*- coding: utf-8 -*-
"""Two reported lines: a drawn-out attack name read as a scream, and a
Rosamia line missing its article.

BATTLE CAPTIONS. アーク is the Graviton ARC, the weapon Touga is told to use
one line earlier ("Touga! Use the Graviton Arc!"). Drawn out as
アァァァァァック it was rendered "Aaaaaaaack!" and "Aaaaargh!!", which turn the
attack name into a cry of pain. The file's own convention for a drawn-out
attack is to stretch the WORD - "Graviton Tornadooo!" for トルネードォォ,
"Sol Graviton Crusheeeer!" for クラッシャァァ, "Graviton Swooooord!" for
ソードォォォ - so these become "Aaaaaarc".

Every replacement holds its field's byte length, NUL-padded: scripted attack
sequences are fetched BY BYTE OFFSET from tables this tool does not rebuild.

ROSAMIA. her japanese line shipped as
"Spacenoids drop the sky...! And it destroyed the world!" - no article, and
"it" with nothing to refer to. "drop the sky" itself is right and is her
recurring phrase (cf. 「空を落とす者達は許さない…！」), so only the article and
the pronoun change. 73 bytes into a 79-byte slot, wrapped 33/31 columns.

Usage: fix_graviton_arc.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
SRVC_LBA, SRVC_SECTORS = 1313214, 1700
STAGE_LBA, STAGE_SIZE = 1651029, 3910128

CAPTIONS = {
    '"Graviton Aaaaaaaack!"':  '"Graviton Aaaaaarc!"',
    '"Graviton! Aaaaaaaack!"': '"Graviton! Aaaaaarc!"',
    '"Graviton! Aaaaargh!!"':  '"Graviton! Aaaaaarc!!"',
}

STAGE_LINES = {
    50: {
        "Rosamia\n「Spacenoids drop the sky...! And\nit destroyed the world!」":
        "Rosamia\n「The Spacenoids drop the sky...!\nAnd that destroyed the world!」",
    },
}


def fix_srvc(f, write):
    f.seek(SRVC_LBA * SEC)
    raw = bytearray(f.read(SRVC_SECTORS * SEC))
    n = 0
    for old, new in CAPTIONS.items():
        ob, nb = old.encode("cp932"), new.encode("cp932")
        assert len(nb) <= len(ob), "%r longer than %r" % (new, old)
        i = 0
        while True:
            i = raw.find(ob, i)
            if i < 0:
                break
            raw[i:i + len(ob)] = nb + b"\x00" * (len(ob) - len(nb))
            n += 1
            i += len(ob)
        print("   %-26s -> %s" % (old, new))
    if write and n:
        f.seek(SRVC_LBA * SEC)
        f.write(bytes(raw))
    return n


def fix_stage(f, write):
    f.seek(STAGE_LBA * SEC)
    raw = bytearray(f.read(STAGE_SIZE))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, d in items if isinstance(h, int) and d is not None)
    by_head = dict((h, d) for h, d in items if isinstance(h, int) and d is not None)
    order = [h for h in heads]
    n = 0
    for rec, table in STAGE_LINES.items():
        hdr = order[rec]
        d = bytearray(by_head[hdr])
        touched = False
        for old, new in table.items():
            ob, nb = old.encode("cp932"), new.encode("cp932")
            i = bytes(d).find(ob)
            if i < 0:
                print("   rec%-3d NOT FOUND %r" % (rec, old[:40]))
                continue
            z = bytes(d).find(b"\x00", i)
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            slot = k - i - 1
            assert len(nb) <= slot, "needs %d, slot %d" % (len(nb), slot)
            # hold the field's extent so no intra-record offset shifts
            d[i:k] = nb + b"\x00" * (k - i - len(nb))
            print("   rec%-3d %d -> %d bytes in a %d slot" % (rec, len(ob), len(nb), slot))
            n += 1
            touched = True
        if not touched or not write:
            continue
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % rec
        raw[hdr:hdr + len(blob)] = blob
        for j in range(hdr + len(blob), nxt):
            raw[j] = 0
    if write and n:
        after = [h for h, d in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and d is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(STAGE_LBA * SEC)
        f.write(bytes(raw))
    return n


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    print("SRVC captions:")
    a = fix_srvc(f, write)
    print("STAGE dialogue:")
    b = fix_stage(f, write)
    f.close()
    print("\n%d caption(s), %d line(s)" % (a, b))
    if not write:
        print("(dry run - pass --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
