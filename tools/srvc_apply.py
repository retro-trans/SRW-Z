# -*- coding: utf-8 -*-
"""Apply the English battle voice lines to BTL/SRVC.BIN and splice into an ISO.

SRVC IS byte-budgeted for scripted attack sequences. srvc.build() recomputes
every INDEX offset, so index-addressed captions (the random battle quotes) may
change length freely - that was the old assumption and it is only half true.
The multi-line sequences a weapon plays (Minerva/Tannhauser: Talia "This ship
now begins attack!" -> Arthur "Roger! All, battle stations!" -> ...) are
fetched BY BYTE OFFSET from tables we do not rebuild. One over-long string
slides every offset after it in its block, and the sequence then shows the
wrong line, the same line twice, "...", or a line missing its opening quote
(a mid-string read). All four were visible on screen in 0.8.52.

    INVARIANT: every replacement string must be EXACTLY the byte length of
    the Japanese string it replaces. Shorter is padded (below); longer is a
    hard error - shorten the text instead (tools/srvc_fit.py).

The original assumption, kept for context: srvc.build() recomputes every index offset and
re-emits SRVC.SEG, so lines may change length freely. English is 1 byte/char
against Japanese 2, so the file normally SHRINKS and stays in place; if it ever
grows past its 1618 sectors it relocates into the DMY padding, and then BOTH the
ISO9660 directory record AND the game's own file table have to move, because
libcdvd reads the latter and ignores the former (a lesson that cost a full debug
cycle on COMPDATA).

File-table entry layout: the path string `\\BTL\\SRVC.BIN;1` starts a 0x28-byte
name field, followed by [u32 LBA][u32 size_in_sectors].

Only strings that pass srvc_work.is_quote() are touched; every other string -
including the binary records that merely decode as kanji - is copied through
byte for byte.

Usage: srvc_apply.py <iso> [--dry]
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc
from patch import encode
from srvc_fit import fit
from srvc_records import resolve, pool_offsets, new_position
from srvc_work import inner, is_quote, load_blocks

WORK = r"E:\Projects\SRW Z\_work"
SECTOR = 2048
ORIG_LBA, ORIG_SECTORS = 1313214, 1618
SEG_LBA = 1309609
NEW_LBA = 1826000                 # DMY padding, clear of the zkn RELOC block
NAME_BIN = b"\\\\BTL\\\\SRVC.BIN;1"


def build_map():
    items = json.load(io.open(os.path.join(WORK, "analysis", "srvc_work.json"),
                              encoding="utf-8"))
    en = json.load(io.open(os.path.join(WORK, "analysis", "srvc_en.json"),
                           encoding="utf-8"))
    m = {}
    for x in items:
        v = en.get(str(x["i"]))
        if v:
            m[x["jp"]] = v
    return m, len(items), len(en)


def build_head_map():
    """HEAD-TRUNCATED quotes: end with 」 but have no opening 「.

    108 strings are like this IN THE ORIGINAL FILE (verified against the
    untouched extract), so is_quote() - which requires a leading 「 - has always
    skipped them and they still shipped Japanese. Keyed by the exact decoded
    string, since inner() cannot normalise something with no opener.
    """
    wp = os.path.join(WORK, "analysis", "srvc_head_work.json")
    ep = os.path.join(WORK, "analysis", "srvc_head_en.json")
    if not (os.path.exists(wp) and os.path.exists(ep)):
        return {}
    items = json.load(io.open(wp, encoding="utf-8"))
    en = json.load(io.open(ep, encoding="utf-8"))
    return {x["jp"]: en[str(x["i"])] for x in items if str(x["i"]) in en}


def main():
    iso_path = sys.argv[1]
    dry = "--dry" in sys.argv
    # Which renderer draws these? The COMPDATA pilot defeat/retreat quotes share
    # the battle message box and are documented as going through the DIALOGUE
    # path as raw ASCII, so that is the default. If an in-game test shows the
    # MENU reader (0x13A290) instead, every . and digit would be eaten as a
    # control code - rerun with --menu and rebuild, no retranslation needed.
    # MENU encoding, proven in game: this box is drawn by the menu reader
    # (0x13A290), where bytes 0x2E-0x3D (. / 0-9 : ; < =) are CONTROL CODES that
    # also swallow a parameter byte. Written as raw ASCII, '"..."' rendered as a
    # single quote mark and every line lost everything from its first full stop
    # onward. Menu encoding emits those characters in their fullwidth forms, so
    # they draw as characters - at 2 bytes and 2 columns each.
    mode = ("ascii" if "--ascii" in sys.argv
            else "menu" if "--fullwidth-digits" in sys.argv else "menuhw")
    # The animation quote box CONSUMES the line from the front and draws what is
    # left - save states caught it holding 'orm!!"', 'orgive you!...' and finally
    # nothing at all, for the same speaker at different moments. Japanese is 2
    # bytes per character, so an original line has twice the bytes of our ASCII
    # and survives the animation; ours is eaten early.
    #
    # Padding at the FRONT gives the box filler to consume before it reaches the
    # words. Padding to the ORIGINAL byte length is also exactly the original
    # display width: N Japanese bytes = N/2 fullwidth chars = N columns, and N
    # padded ASCII bytes = N columns too. So this cannot make a line wider than
    # the one the game already drew there.
    free = "--free" in sys.argv
    pad = "--nopad" not in sys.argv and not free
    print("encoding mode: %s | pad to original byte length: %s"
          % (mode, "yes (trailing)" if pad else "no"))
    data, seg, blocks = load_blocks()
    m, ntotal, ndone = build_map()
    print("worklist %s lines, %s translated" % ("{:,}".format(ntotal),
                                                "{:,}".format(ndone)))

    seq_records, seq_unres = resolve(blocks)
    seq_offs_old = {bi: pool_offsets(blocks[bi].strings) for bi in seq_records}
    print("sequence records resolved: %d across %d blocks (%d unresolved)"
          % (sum(len(v) for v in seq_records.values()), len(seq_records),
             len(seq_unres)))

    hm = build_head_map()
    print("head-truncated quotes with a translation: %d" % len(hm))
    hit = miss = nhead = 0
    overlong, tiers = [], {}
    for b in blocks:
        if not b.has_text:
            continue
        out = []
        for s in b.strings:
            if is_quote(s):
                key = inner(s.decode("cp932"))
                v = m.get(key)
                if v:
                    enc = encode('"' + v + '"', mode)
                    if len(enc) > len(s) and not free:
                        overlong.append((len(enc) - len(s), len(s), v))
                        fitted, tier = fit(v, len(s) - 2, lambda u: encode(u, mode))
                        enc = encode('"' + fitted + '"', mode)
                        tiers[tier] = tiers.get(tier, 0) + 1
                    # Pad AFTER the text, never before. Leading spaces keep the
                    # byte length right but INDENT the line and push it onto an
                    # extra row that falls out of the box - v1.33 shipped that
                    # and it was clearly visible. Trailing spaces are invisible
                    # and leave the text where the original started.
                    if pad and len(enc) < len(s):
                        enc = enc + b" " * (len(s) - len(enc))
                    assert free or len(enc) == len(s), "budget broken"
                    out.append(enc)
                    hit += 1
                    continue
                miss += 1
            else:
                # head-truncated quote (no opening 「) - see build_head_map
                try:
                    u = s.decode("cp932")
                except UnicodeDecodeError:
                    u = None
                hv = hm.get(u) if u else None
                if hv:
                    enc = encode('"' + hv + '"', mode)
                    if len(enc) > len(s) and not free:
                        overlong.append((len(enc) - len(s), len(s), hv))
                        fitted, tier = fit(hv, len(s) - 2, lambda u: encode(u, mode))
                        enc = encode('"' + fitted + '"', mode)
                        tiers[tier] = tiers.get(tier, 0) + 1
                    if pad and len(enc) < len(s):
                        enc = enc + b" " * (len(s) - len(enc))
                    assert free or len(enc) == len(s), "budget broken"
                    out.append(enc)
                    nhead += 1
                    continue
            out.append(s)
        b.strings = out
    print("slots replaced %s (+%s head-truncated), left Japanese %s"
          % ("{:,}".format(hit), "{:,}".format(nhead), "{:,}".format(miss)))

    if overlong:
        names = {0: "as written", 1: "ellipsis", 2: "tidy", 3: "contractions",
                 4: "CLIPPED - rewrite by hand"}
        print("over budget: %d lines refitted %s"
              % (len(overlong), {names[k]: v for k, v in sorted(tiers.items())}))
        json.dump(sorted(([d, b, t] for d, b, t in overlong), reverse=True),
                  io.open(os.path.join(WORK, "analysis", "srvc_fitted.json"),
                          "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    nb, nseg = srvc.build(blocks)
    if free:
        # FREE MODE: strings changed length, so rewrite every sequence
        # record's f2 (target offset relative to its unit anchor) for the
        # new layout. f2 sits at bytes +4..+5 of the 8-byte cell no matter
        # how the cell was parsed, so patch the serialized bytes directly.
        nb = bytearray(nb)
        starts = [struct.unpack("<I", nseg[i * 4:i * 4 + 4])[0]
                  for i in range(len(nseg) // 4)]
        patched = 0
        for bi, recs in seq_records.items():
            b = blocks[bi]
            offs_new = pool_offsets(b.strings)
            offs_old = seq_offs_old[bi]
            pool = starts[bi] + len(b.head) + 8 * len(b.ids)
            for r, target, anchor in recs:
                f2 = offs_new[target] - offs_new[anchor]
                assert 0 <= f2 < 0x10000, (
                    "block %d: f2 out of range (%d)" % (bi, f2))
                nr = new_position(r, offs_old, offs_new)
                nb[pool + nr + 4:pool + nr + 6] = struct.pack("<H", f2)
                patched += 1
        nb = bytes(nb)
        print("free mode: %d sequence records repointed" % patched)
    else:
        assert len(nb) == len(data), (
            "SRVC changed size by %+d bytes - byte offsets into it would slide"
            % (len(nb) - len(data)))
    print("SRVC.BIN %s -> %s bytes (%+d), SEG %d -> %d"
          % ("{:,}".format(len(data)), "{:,}".format(len(nb)),
             len(nb) - len(data), len(seg) * 4, len(nseg)))

    # re-parse what we are about to ship: the index/pool must still tile
    chk = srvc.parse(nb, srvc.read_seg(nseg))
    assert len(chk) == len(blocks), "block count changed"
    assert sum(1 for x in chk if x.has_text) == sum(1 for x in blocks if x.has_text), \
        "a block stopped parsing - the pool no longer tiles"
    print("re-parse OK: %d blocks, %d with text"
          % (len(chk), sum(1 for x in chk if x.has_text)))

    need = (len(nb) + SECTOR - 1) // SECTOR
    if dry:
        print("dry run; would need %d sectors (have %d)" % (need, ORIG_SECTORS))
        return

    with open(iso_path, "r+b") as iso:
        iso.seek(SEG_LBA * SECTOR)
        iso.write(nseg + b"\x00" * ((-len(nseg)) % SECTOR))
        if need <= ORIG_SECTORS:
            iso.seek(ORIG_LBA * SECTOR)
            iso.write(nb + b"\x00" * (ORIG_SECTORS * SECTOR - len(nb)))
            # A previous build may have RELOCATED the file; writing in place
            # without restoring the pointers would leave the game reading the
            # stale copy in DMY.
            head = bytearray(open(iso_path, "rb").read(4 * 1024 * 1024))
            p = head.find(b"SRVC.BIN;1")
            while p >= 0 and head[p - 7:p] != b"\\\\BTL\\\\":
                p = head.find(b"SRVC.BIN;1", p + 1)
            iso.seek(p + 0x21); iso.write(struct.pack("<I", ORIG_LBA))
            iso.seek(p + 0x25); iso.write(struct.pack("<I", ORIG_SECTORS))
            rec = head.find(b"SRVC.BIN;1", 0x80000) - 33
            iso.seek(rec + 2);  iso.write(struct.pack("<I", ORIG_LBA))
            iso.seek(rec + 6);  iso.write(struct.pack(">I", ORIG_LBA))
            iso.seek(rec + 10); iso.write(struct.pack("<I", len(nb)))
            iso.seek(rec + 14); iso.write(struct.pack(">I", len(nb)))
            print("SRVC.BIN written in place at LBA %d (%d/%d sectors); "
                  "dir + file table reset" % (ORIG_LBA, need, ORIG_SECTORS))
            return
        iso.seek(NEW_LBA * SECTOR)
        iso.write(nb + b"\x00" * ((-len(nb)) % SECTOR))
        head = bytearray(open(iso_path, "rb").read(4 * 1024 * 1024))
        p = head.find(b"SRVC.BIN;1")
        while p >= 0 and head[p - 7:p] != b"\\\\BTL\\\\":
            p = head.find(b"SRVC.BIN;1", p + 1)
        assert p > 0, "file-table entry not found"
        iso.seek(p + 0x21); iso.write(struct.pack("<I", NEW_LBA))
        iso.seek(p + 0x25); iso.write(struct.pack("<I", need))
        rec = head.find(b"SRVC.BIN;1", 0x80000) - 33
        iso.seek(rec + 2);  iso.write(struct.pack("<I", NEW_LBA))
        iso.seek(rec + 6);  iso.write(struct.pack(">I", NEW_LBA))
        iso.seek(rec + 10); iso.write(struct.pack("<I", len(nb)))
        iso.seek(rec + 14); iso.write(struct.pack(">I", len(nb)))
        print("SRVC.BIN RELOCATED to LBA %d (%d sectors); dir + file table patched"
              % (NEW_LBA, need))


if __name__ == "__main__":
    main()
