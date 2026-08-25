# -*- coding: utf-8 -*-
"""Option-3 FIX pass: corrected wrap widths + link-rendering variants.

Feedback from the calibration build:
  * SCENE: keep all 3 lines INSIDE the light background panel (~36 half-cols).
  * IN-GAME: text ran off the right SCREEN edge (~28 half-cols safe).
  * LINK: the 《 marker draws as a FULLWIDTH space (huge gap) and the underline
    overflowed because the link sat at the line's right edge. Drop literal 『』,
    keep links off the edge, show variants.

Each width line ends with '|' at the target column so the exact boundary is
visible. Same relocate+repoint+zero mechanism.
"""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_fix.bin")

ROWS = {7: (0x5710, 66), 8: (0x5760, 58), 9: (0x57a0, 58),
        142: (0x84a0, 31), 144: (0x84e0, 95), 146: (0x8560, 91)}


def bar(text, width):
    """text padded with dots to width-1, then '|' as the boundary marker."""
    t = text[:width - 1]
    return t + "." * (width - 1 - len(t)) + "|"


IG, SC = 28, 36   # in-game / scene target widths
TESTS = {
    # IN-GAME width test (rows 7/9) + link variants (row 8)
    7:  ("Denzel", [bar("In-game width, boundary", IG),
                    bar("Second line same width", IG),
                    bar("Third line all on screen", IG)]),
    8:  ("Toby",   ["Bare link: 《Glory Star》 ok?",
                    "Mid: go 《Glory Star》 team",
                    "Brackets: 『《Glory Star》』"]),
    9:  ("Denzel", ["In-game 3-line cap holds,",
                    "no black line, on screen."]),
    # SCENE width test (rows 142/146) + link variants (row 144)
    142:("Jerid",  [bar("Scene width, panel edge", SC),
                    bar("Second line same width", SC),
                    bar("Third line in light panel", SC)]),
    144:("Setsuko",["Bare link: 《Glory Star》 tidy?",
                    "Mid: the 《Glory Star》 members",
                    "Brackets: 『《Glory Star》』 here"]),
    146:("Setsuko",["Scene 3-line cap holds,",
                    "all inside the light panel."]),
}


def build_string(row):
    spk, lines = TESTS[row]
    return ("\n".join([spk] + lines)).encode("cp932") + b"\x00"


def replace_ptr(buf, oldp, newp):
    ob, nb, cnt, i = struct.pack("<I", oldp), struct.pack("<I", newp), 0, 0
    while True:
        j = buf.find(ob, i)
        if j < 0:
            break
        if j % 4 == 0:
            buf[j:j + 4] = nb; cnt += 1; i = j + 4
        else:
            i = j + 1
    return cnt


def main():
    with open(BASE_ISO, "rb") as f:
        f.seek(STAGE_LBA * SECTOR)
        stage = bytearray(f.read(STAGE_SIZE))
    rec = bytearray(banlz.decompress_all(bytes(stage))[1][1])
    orig_len = len(rec)
    total, flags, at = banlz.parse_header(bytes(stage), SLOT_START)
    new_off = {}
    for row in sorted(TESTS):
        new_off[row] = len(rec)
        rec += build_string(row)
    for row in sorted(TESTS):
        off, nb = ROWS[row]
        assert replace_ptr(rec, BASE + off, BASE + new_off[row]) >= 1
        for x in range(off, off + nb):
            rec[x] = 0
    blob = banlz.compress_record(bytes(rec), flags)
    assert banlz.decompress_record(blob)[0] == bytes(rec)
    slot = SLOT_END - SLOT_START
    print("record %d->%d; recompressed %d / slot %d -> %s"
          % (orig_len, len(rec), len(blob), slot,
             "FITS" if len(blob) <= slot else "TOO BIG"))
    assert len(blob) <= slot
    stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
    assert banlz.decompress_all(bytes(stage))[1][1] == bytes(rec)
    import banlz_strict as bs
    t2, fl2, at2 = banlz.parse_header(bytes(stage), SLOT_START)
    print("strict problems:", len(bs.verify(bytes(stage), at2, t2)[1]))
    shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR); f.write(stage)
    print("wrote", OUT_ISO)


if __name__ == "__main__":
    main()
