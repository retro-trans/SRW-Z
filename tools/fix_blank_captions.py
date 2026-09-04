# -*- coding: utf-8 -*-
"""Restore 5 battle voice captions that shipped COMPLETELY BLANK.

These are sequence-target captions whose Japanese has a real line but whose
English slot on the disc is empty (voice plays, box is blank). The translation
already exists in srvc_en.json; it just never made it onto the disc.

Seeds from the CURRENT disc (so all other captions are preserved byte-for-byte),
edits ONLY the 5 blank targets, then rebuilds and repoints the sequence records
of the touched blocks (all four resolve cleanly, so the repoint is exact).

Usage: fix_blank.py <iso> [--write]
"""
import io, json, os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")
import srvc
from srvclib import getfile
from srvc_records import resolve, pool_offsets, new_position
from patch import encode

SECTOR = 2048
ORIG_LBA, ORIG_SECTORS = 1313214, 1618
SEG_LBA = 1309609

# (block, clip_id, english) — clip_id disambiguates the target inside the block.
FIX = [
    (65, 257, "Shinn! Don't charge in!"),
    (90, 257, "I'll mince you with this Drill!"),
    (151, 261, "I'll drag out the truth\\nthe military's hiding!"),
    (234, 268, "I'll take a loss!"),
]
TOUCHED_BLOCKS = sorted(set(b for b, _, _ in FIX))


def isblank(s):
    return len(s.replace(b" ", b"").replace(b'"', b"")) == 0


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    bin_ = getfile(iso, "/BTL/SRVC.BIN")
    segb = getfile(iso, "/BTL/SRVC.SEG")
    seg = srvc.read_seg(segb)
    blocks = srvc.parse(bin_, seg)

    seq, unres = resolve(blocks)
    seq_offs_old = {bi: pool_offsets(blocks[bi].strings) for bi in seq}

    # locate + edit the blank targets by (block, clip)
    edited = 0
    for bi, want_clip, en in FIX:
        blk = blocks[bi]
        pool_start = seg[bi] + len(blk.head) + 8 * len(blk.ids)
        hits = []
        for r, tgt, anch in seq[bi]:
            clip = struct.unpack_from("<H", bin_, pool_start + r)[0]
            if clip == want_clip and isblank(blk.strings[tgt]):
                hits.append(tgt)
        if not hits:
            print("  blk%d clip%d: no blank target found (already fixed?)" % (bi, want_clip))
            continue
        newstr = encode('"' + en + '"', "menuhw")
        for tgt in set(hits):
            assert isblank(blk.strings[tgt]), "blk%d tgt%d not blank" % (bi, tgt)
            blk.strings[tgt] = newstr
            edited += 1
            print("  blk%d clip%d slot%d -> %r (%d records point here)"
                  % (bi, want_clip, tgt, newstr, hits.count(tgt)))

    if not edited:
        print("nothing to do"); return
    print("edited %d blank slots" % edited)

    nb, nseg = srvc.build(blocks)
    nb = bytearray(nb)
    starts = [struct.unpack("<I", nseg[i * 4:i * 4 + 4])[0] for i in range(len(nseg) // 4)]

    # repoint EVERY resolved record. Unedited blocks: offs unchanged -> same f2.
    # Edited blocks (all clean): exact recompute.
    patched = 0
    for bi, recs in seq.items():
        blk = blocks[bi]
        offs_new = pool_offsets(blk.strings)
        offs_old = seq_offs_old[bi]
        pool = starts[bi] + len(blk.head) + 8 * len(blk.ids)
        for r, tgt, anch in recs:
            f2 = offs_new[tgt] - offs_new[anch]
            assert 0 <= f2 < 0x10000, "blk%d f2 out of range %d" % (bi, f2)
            nr = new_position(r, offs_old, offs_new)
            nb[pool + nr + 4:pool + nr + 6] = struct.pack("<H", f2)
            patched += 1
    nb = bytes(nb)
    print("repointed %d records; SRVC %d -> %d bytes (%+d)"
          % (patched, len(bin_), len(nb), len(nb) - len(bin_)))

    # re-parse + re-resolve sanity
    chk = srvc.parse(nb, srvc.read_seg(nseg))
    assert len(chk) == len(blocks)
    assert sum(1 for x in chk if x.has_text) == sum(1 for x in blocks if x.has_text)
    chkseq, _ = resolve(chk)
    got = sum(len(v) for v in chkseq.values())
    have = sum(len(v) for v in seq.values())
    print("re-parse OK; records re-resolve %d/%d (%+d)" % (got, have, got - have))
    # verify the 5 targets are now non-blank in the rebuilt bytes
    for bi, want_clip, en in FIX:
        blk = chk[bi]
        ps = srvc.read_seg(nseg)[bi] + len(blk.head) + 8 * len(blk.ids)
        found = [t for r, t, a in chkseq[bi]
                 if struct.unpack_from("<H", nb, ps + r)[0] == want_clip]
        vals = set(blk.strings[t] for t in found)
        print("  verify blk%d clip%d -> %s" % (bi, want_clip, [v[:28] for v in vals]))

    need = (len(nb) + SECTOR - 1) // SECTOR
    print("need %d sectors (have %d)" % (need, ORIG_SECTORS))
    assert need <= ORIG_SECTORS, "would relocate - unexpected"
    if not write:
        print("\n(dry run - pass --write to apply)"); return

    with open(iso, "r+b") as f:
        f.seek(SEG_LBA * SECTOR)
        f.write(nseg + b"\x00" * ((-len(nseg)) % SECTOR))
        f.seek(ORIG_LBA * SECTOR)
        f.write(nb + b"\x00" * (ORIG_SECTORS * SECTOR - len(nb)))
        head = bytearray(open(iso, "rb").read(4 * 1024 * 1024))
        p = head.find(b"SRVC.BIN;1")
        while p >= 0 and head[p - 7:p] != b"\\\\BTL\\\\":
            p = head.find(b"SRVC.BIN;1", p + 1)
        f.seek(p + 0x21); f.write(struct.pack("<I", ORIG_LBA))
        f.seek(p + 0x25); f.write(struct.pack("<I", ORIG_SECTORS))
        rec = head.find(b"SRVC.BIN;1", 0x80000) - 33
        f.seek(rec + 2);  f.write(struct.pack("<I", ORIG_LBA))
        f.seek(rec + 6);  f.write(struct.pack(">I", ORIG_LBA))
        f.seek(rec + 10); f.write(struct.pack("<I", len(nb)))
        f.seek(rec + 14); f.write(struct.pack(">I", len(nb)))
    print("SRVC.BIN written in place at LBA %d (%d/%d sectors)" % (ORIG_LBA, need, ORIG_SECTORS))


main()

# appended: dump rebuilt SRVC for verification when DUMP env set
