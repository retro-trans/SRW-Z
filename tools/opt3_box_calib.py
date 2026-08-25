# -*- coding: utf-8 -*-
"""Option-3 BOX CALIBRATION: exact width + 3-line cap for both dialogue boxes.

Patches rec001 (stage 1) to place calibrated test strings in BOTH boxes at once
so one build tests both:
  * IN-GAME over-map box  -> rows 7/8/9   (Denzel/Toby/Denzel opening lines)
  * SCENE big box         -> rows 142/144/146 (Jerid/Jerid/Setsuko corridor)

Each box gets: a 50-digit ruler line (count where it wraps = exact width),
a 3-line max-fill line (confirms 3 lines show cleanly, no clipped 4th line),
and a short line. Same proven relocate+repoint+zero mechanism.
"""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_boxcalib.bin")

# row -> (offset, nbytes) from rec001_script.json (same offsets in EN, in-place)
ROWS = {7: (0x5710, 66), 8: (0x5760, 58), 9: (0x57a0, 58),
        142: (0x84a0, 31), 144: (0x84e0, 95), 146: (0x8560, 91)}

RULER = "1234567890123456789012345678901234567890123456789|"  # 50 + end bar

# Each entry: (speaker, [line1, line2, line3])  -- max 3 dialogue lines.
TESTS = {
    # IN-GAME box (target ~42 cols). Keep filler <=40 so only the ruler tests width.
    7:  ("Denzel", [RULER,
                    "IN-GAME box: count digits above until it",
                    "wraps -> that is this box's line width."]),
    8:  ("Toby",   ["Max-fill line one, about forty chars wide here",
                    "Max-fill line two, same width to test three rows",
                    "Max-fill line three -- is there a clipped 4th?"]),
    9:  ("Denzel", ["Link test -- the 《Glory Star》 team name",
                    "should show colored + underlined here."]),
    # SCENE box (target ~46 cols).
    142:("Jerid",  [RULER,
                    "SCENE box: count digits until it wraps ->",
                    "this box is wider than the in-game one."]),
    144:("Setsuko",["Max-fill scene line one, roughly forty-four wide.",
                    "Max-fill scene line two at the same width again.",
                    "Max-fill scene line three -- any clipped 4th line?"]),
    146:("Setsuko",["Scene link test: 『《Glory Star》』",
                    "should render colored + underlined."]),
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
    recs = banlz.decompress_all(bytes(stage))
    rec = bytearray(recs[1][1])
    orig_len = len(rec)
    total, flags, at = banlz.parse_header(bytes(stage), SLOT_START)

    new_off = {}
    for row in sorted(TESTS):
        new_off[row] = len(rec)
        rec += build_string(row)
    for row in sorted(TESTS):
        off, nb = ROWS[row]
        cnt = replace_ptr(rec, BASE + off, BASE + new_off[row])
        assert cnt >= 1, "row %d: no pointer" % row
        for x in range(off, off + nb):
            rec[x] = 0
        s = build_string(row)
        print("row %3d: %d ref(s), %d dialogue lines, %d bytes"
              % (row, cnt, s.count(b"\n"), len(s)))

    blob = banlz.compress_record(bytes(rec), flags)
    assert banlz.decompress_record(blob)[0] == bytes(rec)
    slot = SLOT_END - SLOT_START
    print("record %d->%d; recompressed %d / slot %d -> %s"
          % (orig_len, len(rec), len(blob), slot,
             "FITS" if len(blob) <= slot else "TOO BIG"))
    assert len(blob) <= slot
    stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
    chk = banlz.decompress_all(bytes(stage))
    assert all(r[1] is not None for r in chk) and chk[1][1] == bytes(rec)
    try:
        import banlz_strict as bs
        t2, fl2, at2 = banlz.parse_header(bytes(stage), SLOT_START)
        print("strict problems:", len(bs.verify(bytes(stage), at2, t2)[1]))
    except Exception as e:
        print("strict skipped:", e)
    shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR); f.write(stage)
    print("wrote", OUT_ISO)


if __name__ == "__main__":
    main()
