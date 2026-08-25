# -*- coding: utf-8 -*-
"""Point the spirit-command UI at the private micro-glyph codes.

The spirit list and the search-screen strip show each spirit as one kanji
(熱魂閃不鉄集必加迅覚手狙直幸努乱分).  patch_micro_glyphs.py draws a
two-letter pair ("Va", "So", "Fo", ...) into a PRIVATE full-width cell per
spirit; this tool swaps the kanji in every UI string for that private
code.  Both are 2 bytes and both are one full-width cell, so byte lengths
and pixel positions are untouched - which matters because the game paints
the pilot's own spirits in WHITE over the gray list on a fixed 24 px
pitch (0.8.41 used ASCII pairs here and they drifted out of register).

Private codes, not the kanji's own cell, because a master-font cell is
global: the tutorial bank still writes 加/手/分/必/集/直/不 in ordinary
Japanese sentences (359 of them), and those would have turned into
"AcMeAn..." too.  SJIS lead row 0x85 is unassigned, so nothing else can
ever land on these cells.

Sources in the ELF:
  0x3FA290  spirit record table, stride 0x10 = [name, kanji, desc, ?]
  0x442530..0x4425F0  five variants of the 16-kanji strip
Also translates the three record names that were still bare kanji
(魂 -> Soul, 愛 -> Love, 絆 -> Bond).  魂's record aliased its name AND
kanji field to one 16-byte slot, so that slot is split.

Usage: patch_spirit_abbrev.py <iso> [--revert] [--names-only]  (idempotent)
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch_micro_glyphs import SPIRITS, PRIV_BASE, BLANK_CODE

ELF_LBA, SECTOR = 455, 2048
VBASE, FOFF = 0x100000, 0x1A80
TABLE = 0x3FA290
# all six entries of the variant table at 0x42C220 - [4] and [5] are the
# TWO-ROW forms (newline after the 8th), [2]/[3] carry the "/" separator
STRIPS = [0x442530, 0x442560, 0x442590, 0x4425C0, 0x4425F0, 0x442620]
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "analysis", "spirit_abbrev_jp.json")

PRIV = {ch: PRIV_BASE + i for i, (ch, _pair) in enumerate(SPIRITS)}
PAIR = {ch: pair for ch, pair in SPIRITS}
NAMES = {"魂": "Soul", "愛": "Love", "絆": "Bond"}

# The white "spirits this pilot has" overlay is built by 0x35E370: it copies
# the strip, then overwrites every unowned slot with the character at
# 0x42C268 and, when the "/" split applies, re-joins the tail through the
# format string at 0x442648.  Both are a FULL-WIDTH SPACE, which patch_hwfont
# advances by 13 px (that space is the English word space) - so the white
# string drew narrower than the gray one and slid left by a whole cell.
# Point both at the blank private CELL: same advance path as the pairs.
MASKS = [(0x42C268, bytes.fromhex("814000")),      # mask char + NUL
         (0x442648, bytes.fromhex("81402573"))]    # "　%s"

SOUL_KANJI_VA = 0x4357B0          # record 0x3FA3B0 aliases name == kanji
SOUL_NAME_VA = 0x4357B4           # split-off name slot inside the same 16 B


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    names_only = "--names-only" in sys.argv
    iso = open(iso_path, "r+b")
    iso.seek(ELF_LBA * SECTOR)
    elf = bytearray(iso.read(3471624))
    fo = lambda va: va - VBASE + FOFF

    def cstr(va):
        i = fo(va)
        return bytes(elf[i:elf.index(b"\x00", i)])

    def room(va):
        i = fo(va)
        j = elf.index(b"\x00", i)
        while elf[j] == 0:
            j += 1
        return j - i

    def put(va, blob):
        elf[fo(va):fo(va) + len(blob)] = blob

    if revert:
        saved = json.load(open(BACKUP))
        for key, hexs in saved.items():
            if key.startswith("ptr"):
                struct.pack_into("<I", elf, fo(int(key[3:])), int(hexs, 16))
            else:
                put(int(key), bytes.fromhex(hexs))
        print("restored %d entries" % len(saved))
    else:
        # keep whatever an earlier run recorded: re-running must not
        # overwrite the ORIGINAL bytes with already-patched ones
        try:
            saved = json.load(open(BACKUP))
        except Exception:
            saved = {}

        def save(va, n):
            saved.setdefault("%d" % va, bytes(elf[fo(va):fo(va) + n]).hex())

        if not names_only:
            # 1) the five strip variants: kanji -> private code, in place.
            #    Newlines and the full-width slash are copied through.
            for va in STRIPS:
                raw, out, i = cstr(va), bytearray(), 0
                while i < len(raw):
                    b = raw[i]
                    if b == (PRIV_BASE >> 8):          # already a private code
                        out += raw[i:i + 2]
                        i += 2
                    elif 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF:
                        ch = raw[i:i + 2].decode("cp932")
                        out += (struct.pack(">H", PRIV[ch]) if ch in PRIV
                                else raw[i:i + 2])
                        i += 2
                    else:                              # newline, ASCII
                        out += raw[i:i + 1]
                        i += 1
                assert len(out) == len(raw), (hex(va), len(out), len(raw))
                save(va, len(out))
                put(va, bytes(out))
            print("%d strip variants -> private codes" % len(STRIPS))
            # the white overlay's padding must advance like a cell, not
            # like the 13 px English space
            for va, orig in MASKS:
                cur = bytes(elf[fo(va):fo(va) + len(orig)])
                want = struct.pack(">H", BLANK_CODE) + orig[2:]
                assert cur in (orig, want), (hex(va), cur.hex())
                save(va, len(orig))
                put(va, want)
                print("mask %#x %s -> %s" % (va, orig.hex(), want.hex()))

        done = set()
        for k in range(64):
            rec = TABLE + k * 0x10
            name_va, kan_va = struct.unpack_from("<2I", elf, fo(rec))
            kan = None
            if 0x400000 <= kan_va <= 0x450000:
                try:
                    kan = cstr(kan_va).decode("cp932")
                except Exception:
                    kan = None
            # 2) abbreviation slot -> private code (exactly 2 bytes, so
            #    anything sharing the slot's tail, like "Soul", survives)
            if kan in PRIV and kan_va not in done and not names_only:
                done.add(kan_va)
                save(kan_va, 2)
                put(kan_va, struct.pack(">H", PRIV[kan]))
                print("%s -> %s (%#06x)" % (kan, PAIR[kan], PRIV[kan]))
            # 3) 魂's record points name AND kanji at one slot: give the
            #    name its own string in the slot's free tail
            if kan_va == SOUL_KANJI_VA and name_va == SOUL_KANJI_VA:
                save(kan_va, 16)
                saved["ptr%d" % rec] = "%08x" % name_va
                tail = bytes(elf[fo(kan_va):fo(kan_va) + 2])
                put(kan_va, tail + bytes([0, 0]) + b"Soul" + bytes(8))
                struct.pack_into("<I", elf, fo(rec), SOUL_NAME_VA)
                print("Soul name split to %#x" % SOUL_NAME_VA)
                continue
            # 4) record names that are still a bare kanji
            if 0x400000 <= name_va <= 0x450000 and name_va != SOUL_KANJI_VA:
                try:
                    nm = cstr(name_va).decode("cp932")
                except Exception:
                    continue
                if nm in NAMES and name_va not in done:
                    done.add(name_va)
                    cap = room(name_va)
                    new = NAMES[nm].encode("ascii")
                    assert len(new) < cap, (hex(name_va), cap)
                    save(name_va, cap)
                    put(name_va, new + bytes(cap - len(new)))
                    print("name %s -> %s" % (nm, NAMES[nm]))
        json.dump(saved, open(BACKUP, "w"), indent=1)

    iso.seek(ELF_LBA * SECTOR)
    iso.write(bytes(elf))
    iso.close()
    print("done")


if __name__ == "__main__":
    main()
