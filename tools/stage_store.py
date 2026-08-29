# -*- coding: utf-8 -*-
"""Relocate STAGE.BIN and store its records UNCOMPRESSED, so edits are instant.

    RESULT: THIS DOES NOT WORK. Kept as the record of why, so nobody spends
    another evening on it.

    Three builds, one variable each:

        TEST-MOVE   same size, new address        -> WORKS
        TEST-SHIFT  same size, records +16 bytes  -> WORKS
        TEST-STORE  3.13x size, new address       -> HANGS on save load

    So relocating STAGE is safe, and record POSITIONS inside it do not matter
    (every record can slide and the game is fine). What the game will not
    tolerate is the file being three times bigger. Something sizes a buffer
    or a read from the original extent, and 11.7 MB blows it.

    And there is no partial version of this. Store-encoding needs 3.13x, the
    current allocation has 1,557 bytes of slack, and the smallest record needs
    more than that - so not one record can be stored even in the best case.
    Storing only some records buys nothing either: any record left compressed
    still costs the 85-second optimal parse when it is edited.

    The useful finding is the opposite of what was intended: records may move
    freely within STAGE. Nothing indexes their offsets. That is worth knowing
    for any future repack, and it is what TEST-SHIFT proved.


WHY. Every text change has to recompress the records it touched, and the
records must fit fixed slots, so the slow optimal parser is mandatory:

    record 5 (46 KB): slot 17,216 bytes
      greedy, depth   768 -> 17,307   over by 91
      greedy, depth 60,000 -> 17,290  over by 74   (saturates - greedy cannot fit)
      optimal              -> fits, in ~85 seconds

Roughly a third of records need that path, and a single pass over the script
has cost this project well over an hour of wall clock more than once.

THE WAY OUT. The decoder's grammar allows a final literals-only group, so a
record can be "stored" rather than compressed - emitted in O(n) with no match
search at all. Verified against the game's own decompressor: it round-trips.

    record 13, 38,528 bytes of text
      store-encoded : 38,537 bytes in 0.0000 s   round-trips: True
      optimal LZ    : 14,560 bytes in ~85 s

The catch is size: stored, the whole script is 11.7 MB against 3.7 MB
allocated, and NOT ONE of the 205 records fits its current slot. So STAGE has
to move. It goes into DMY.BIN, 117 MB of pure padding that is already home to
the relocated COMPDATA and ZKN banks - verified all-zero at the target.

WHY THIS IS SAFE TO MOVE. The game resolves files through its own table, not
the ISO9660 directory (libcdvd reads the former and ignores the latter - a
lesson COMPDATA already paid for). The entry holds [u32 LBA][u32 sectors] at
name+0x28. SRVC and COMPDATA were both relocated this way and work.

Nothing indexes the record offsets either: of 204 offsets, only 9 appear
anywhere in the ELF, scattered with gaps of hundreds of KB rather than the
4-byte stride a table would have. The row pointers inside a record are RAM
addresses off BASE 0x7566F0, so they do not care where the record sat on disc.

Usage: stage_store.py <iso> [--revert] [--dry-run]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
OLD_LBA, OLD_SIZE = 1651029, 3910128
NEW_LBA = 1766000                 # inside DMY, well clear of COMPDATA at 1823000
NAME = (chr(92) * 2 + "DATA" + chr(92) * 2 + "STAGE.BIN;1").encode()
ISO_NAME = b"STAGE.BIN;1"


def store_record(data, flags=0x15):
    """Header + one literals-only final group. No match search."""
    head = bytearray()
    head += banlz._emit_varint(len(data))
    head += banlz._emit_varint(flags)
    window = 1 << (((flags >> 1) & 0xF) + 8)
    if not (window >= len(data) and (flags & 0x21) == 1):
        if flags & 0x40:
            head += banlz._emit_varint(0)
    head += banlz._emit_varint(0)
    n = len(data)
    g = bytearray([1 << 4 | (0 if n > 15 else n)])
    if n > 15:
        g += banlz._emit_varint(n)
    return bytes(head) + bytes(g) + bytes(data)


def game_table(f):
    f.seek(0)
    boot = bytearray(f.read(0x120000))
    k = boot.find(NAME)
    if k < 0:
        raise SystemExit("STAGE not in the game file table")
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    return k, lba, nsec


def iso_dir_entry(f):
    """Return the absolute file offset of STAGE's ISO9660 directory record."""
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    stack = [(struct.unpack_from("<I", root, 2)[0],
              struct.unpack_from("<I", root, 10)[0])]
    seen = set()
    while stack:
        lba, ln = stack.pop()
        if (lba, ln) in seen:
            continue
        seen.add((lba, ln))
        f.seek(lba * SEC)
        data = f.read(ln)
        p = 0
        while p < len(data):
            rl = data[p]
            if rl == 0:
                p = (p // SEC + 1) * SEC
                if p >= len(data):
                    break
                continue
            flags, nl = data[p + 25], data[p + 32]
            nm = data[p + 33:p + 33 + nl]
            if nm == ISO_NAME:
                return lba * SEC + p
            if flags & 2 and nm not in (b"\x00", b"\x01"):
                stack.append((struct.unpack_from("<I", data, p + 2)[0],
                              struct.unpack_from("<I", data, p + 10)[0]))
            p += rl
    raise SystemExit("STAGE not in the ISO9660 tree")


def main():
    iso = sys.argv[1]
    dry = "--dry-run" in sys.argv
    revert = "--revert" in sys.argv
    f = open(iso, "rb" if dry else "r+b")
    tk, cur_lba, cur_sec = game_table(f)
    de = iso_dir_entry(f)
    print("game table: STAGE at LBA %d, %d sectors" % (cur_lba, cur_sec))

    if "--move-only" in sys.argv:
        # Relocation WITHOUT changing a byte of content, to separate the two
        # variables: same records, same sizes, same compression - new LBA.
        f.seek(cur_lba * SEC)
        blob = f.read(cur_sec * SEC)
        nsec, target = cur_sec, NEW_LBA
        f.seek(target * SEC)
        assert not any(f.read(nsec * SEC)), 'target not empty'
        print('move-only: %d sectors copied verbatim to LBA %d'
              % (nsec, target))
        if not dry:
            f.seek(target * SEC)
            f.write(blob)
            f.seek(tk + 0x28)
            f.write(struct.pack('<II', target, nsec))
            f.seek(de + 2); f.write(struct.pack('<I', target))
            f.seek(de + 6); f.write(struct.pack('>I', target))
        f.close()
        print('done (content untouched)')
        return

    if revert:
        target, blob = OLD_LBA, None
        nsec = OLD_SIZE // SEC + (1 if OLD_SIZE % SEC else 0)
    else:
        f.seek(cur_lba * SEC)
        recs = banlz.decompress_all(f.read(cur_sec * SEC))
        out = bytearray()
        for _h, p in recs:
            if p is None:
                continue
            rec = store_record(bytes(p))
            out += rec
            if len(out) % 16:
                out += b"\x00" * (16 - len(out) % 16)
        blob = bytes(out)
        nsec = (len(blob) + SEC - 1) // SEC
        target = NEW_LBA
        print("stored %d records -> %d bytes (%d sectors), was %d sectors"
              % (len(recs), len(blob), nsec, cur_sec))
        back = banlz.decompress_all(blob)
        assert len(back) == len(recs), "record count changed"
        for i in range(len(recs)):
            assert bytes(back[i][1]) == bytes(recs[i][1]), "rec %d differs" % i
        print("round-trip: all %d records identical" % len(recs))
        f.seek(target * SEC)
        room = f.read(nsec * SEC)
        assert not any(room), "target region is NOT empty - refusing"
        print("target LBA %d verified empty (%d sectors)" % (target, nsec))

    if dry:
        print("(dry run)")
        f.close()
        return
    if blob is not None:
        f.seek(target * SEC)
        f.write(blob + b"\x00" * (nsec * SEC - len(blob)))
    f.seek(tk + 0x28)
    f.write(struct.pack("<II", target, nsec))
    f.seek(de + 2)
    f.write(struct.pack("<I", target))
    f.seek(de + 6)
    f.write(struct.pack(">I", target))          # big-endian copy
    f.seek(de + 10)
    f.write(struct.pack("<I", nsec * SEC))
    f.seek(de + 14)
    f.write(struct.pack(">I", nsec * SEC))
    f.close()
    print("file table + ISO directory now point at LBA %d, %d sectors"
          % (target, nsec))


if __name__ == "__main__":
    main()
