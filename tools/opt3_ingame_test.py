# -*- coding: utf-8 -*-
"""Option-3 IN-GAME (over-map battle box) test.

The corridor test proved repointing works for SCENE dialogue (the 16-byte
[01,speaker,ptr] structs embedded in scenario bytecode). This targets the
OTHER box: the in-game/over-map battle dialogue, whose entries are a clean
32-byte-stride table at the top of the stage record. Rows 7/8/9 of stage 1
(Denzel/Toby/Denzel, the game's opening 3 lines) are the ones the first opt3
test hit -- the ones that showed the black line when left unwrapped.

Mechanism (identical to the corridor test that worked in-game):
  * take the ENGLISH rec001 out of the base ISO's STAGE region,
  * append each new (wrapped) string past the record's end,
  * rewrite every 4-aligned occurrence of the old absolute pointer
    (BASE+old_off) to BASE+new_off,
  * zero the old string bytes to reclaim compression room,
  * recompress into rec001's 17024-byte slot, splice, write a new ISO.
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_ingame.bin")

# row -> (offset, nbytes) in the decompressed record (same in EN, in-place slots)
ROWS = {7: (0x5710, 66), 8: (0x5760, 58), 9: (0x57a0, 58)}


def wrap(text, ncol):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= ncol:
            cur += " " + w
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


NCOL = 28
TESTS = {
    7: ("Denzel", "TEST 1 (fits): a longer in-game line that would have "
        "overflowed the old byte budget but now wraps neatly across the "
        "battle box."),
    8: ("Toby", "TEST 2 (PAGE or CLIP?): a deliberately long in-battle speech "
        "running well past the three lines the over-map box normally shows, to "
        "reveal whether the in-game box pages through every line or clips the "
        "overflow. Line eight. Line nine. Line ten here."),
    9: ("Denzel", "TEST 3 (medium): a moderately expanded reply spanning a few "
        "extra rows, confirming clean wrapping with no black line in the map "
        "box."),
}


def build_string(row):
    spk, body = TESTS[row]
    lines = [spk] + wrap(body, NCOL)
    return ("\n".join(lines)).encode("cp932") + b"\x00"


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
    assert len(recs) == 205
    rec = bytearray(recs[1][1])            # ENGLISH rec001
    orig_len = len(rec)

    total, flags, at = banlz.parse_header(bytes(stage), SLOT_START)

    new_off = {}
    for row in sorted(TESTS):
        s = build_string(row)
        new_off[row] = len(rec)
        rec += s
    for row in sorted(TESTS):
        off, nb = ROWS[row]
        cnt = replace_ptr(rec, BASE + off, BASE + new_off[row])
        print("row %d: repointed %d ref(s)  old=%#x -> new=%#x  (%d lines)"
              % (row, cnt, BASE + off, BASE + new_off[row],
                 build_string(row).count(b"\n")))
        assert cnt >= 1, "no pointer found for row %d" % row
        for x in range(off, off + nb):     # zero old string, reclaim space
            rec[x] = 0

    blob = banlz.compress_record(bytes(rec), flags)
    rt, _ = banlz.decompress_record(blob)
    assert rt == bytes(rec), "round-trip failed"
    slot = SLOT_END - SLOT_START
    print("record %d -> %d bytes; recompressed %d / slot %d -> %s"
          % (orig_len, len(rec), len(blob), slot,
             "FITS" if len(blob) <= slot else "TOO BIG"))
    assert len(blob) <= slot, "does not fit slot"

    stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
    chk = banlz.decompress_all(bytes(stage))
    assert all(r[1] is not None for r in chk) and chk[1][1] == bytes(rec)

    # strict-decode safety on the new record
    try:
        import banlz_strict as bs
        t2, fl2, at2 = banlz.parse_header(bytes(stage), SLOT_START)
        probs = bs.verify(bytes(stage), at2, t2)[1]
        print("strict problems: %d" % len(probs))
    except Exception as e:
        print("strict check skipped:", e)

    # write a fresh ISO with only the STAGE region replaced
    import shutil
    shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR)
        f.write(stage)
    print("wrote", OUT_ISO)


if __name__ == "__main__":
    main()
