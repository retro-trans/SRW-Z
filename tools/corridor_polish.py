# -*- coding: utf-8 -*-
"""Production pass for the corridor scene (rec001 rows 142-211).

Transforms the shipped English:
  * "..." quotes -> 「...」 (also turns the speaker name blue - engine behavior)
  * restores 《term》 glossary links exactly where the JP original had 《》
    (bare form; the linkpos/underline ELF patches make them render tight)
  * de-quotes terms the JP left unmarked ('Glory Star' -> Glory Star)
  * keeps the existing manual line wraps; asserts <=37 display cols, <=3 lines
  * in-place where the bytes fit the original slot, relocate+repoint otherwise
    (old bytes zeroed to reclaim compression space)

Output: iso/srwz_corridor2.bin = srwz_fix3.bin + linkpos/underline ELF patches
        + this rec001.
"""
import os, sys, json, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import patch_linkpos, patch_underline, patch_backlog

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
SLOT_START, SLOT_END = 0xd860, 0x11ae0
BASE = 0x7566f0
ELF_LBA, ELF_SIZE = 455, 3471624
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_fix3.bin")
OUT_ISO  = os.path.join(WORK, "iso", "srwz_corridor2.bin")

OQ, CQ, LO, LC = "\u300c", "\u300d", "\u300a", "\u300b"   # 「 」 《 》

# rows whose JP has 《》 links, and the term substitutions to make
GS, TT, AE = "'Glory Star'", "'Titans'", "'AEUG'"
LINK = {
    144: [(GS, LO+"Glory Star"+LC)],
    146: [(GS, LO+"Glory Star"+LC)],
    150: [(TT, LO+"Titans"+LC)],
    157: [(AE, LO+"AEUG"+LC)],
    161: [(TT, LO+"Titans"+LC)],
    162: [(GS, LO+"Glory Star"+LC)],
    168: [("'Titans''", LO+"Titans"+LC+"'")],
    171: [(GS, LO+"Glory Star"+LC)],
    173: [(TT, LO+"Titans"+LC)],
    174: [(AE, LO+"AEUG"+LC)],
    181: [(GS, LO+"Glory Star"+LC)],
    186: [("'Glory Star's'", LO+"Glory Star"+LC+"'s")],
    191: [(TT, LO+"Titans"+LC)],
    192: [("'AEUG's'", LO+"AEUG"+LC+"'s")],
    195: [(TT, LO+"Titans"+LC)],
    197: [(TT, LO+"Titans"+LC)],
    207: [(GS, LO+"Glory Star"+LC)],
    210: [(TT, LO+"Titans"+LC), (AE, LO+"AEUG"+LC)],
}
# rows whose JP had NO markers on the term -> plain name
DEQUOTE = {
    147: [("'Right Stuff'", "Right Stuff")],
    155: [(GS, "Glory Star")],
    184: [(GS, "Glory Star")],
}

MAXCOL = 37


def disp_width(line):
    w = 0
    for c in line:
        if c in (LO, LC):
            continue                      # markers draw no width now
        w += 2 if ord(c) > 0x7F else 1
    return w


def transform(idx, txt):
    parts = txt.split("\n")
    spk, body = parts[0], parts[1:]
    if not body:
        return None
    joined = "\n".join(body)
    if not (joined.startswith('"') and joined.endswith('"')):
        return None                       # thought () rows etc: untouched
    inner = joined[1:-1]
    for old, new in LINK.get(idx, []) + DEQUOTE.get(idx, []):
        inner = inner.replace(old, new)
    assert "'Glory Star'" not in inner and "'Titans'" not in inner \
        and "'AEUG'" not in inner, "missed quote in row %d: %r" % (idx, inner)
    out = OQ + inner + CQ
    lines = out.split("\n")
    assert len(lines) <= 3, "row %d: %d lines" % (idx, len(lines))
    for ln in lines:
        assert disp_width(ln) <= MAXCOL, \
            "row %d line too wide (%d): %r" % (idx, disp_width(ln), ln)
    return spk + "\n" + out


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
    rows = json.load(open(os.path.join(WORK, "analysis", "rec001_script.json"),
                          encoding="utf-8"))
    with open(BASE_ISO, "rb") as f:
        f.seek(STAGE_LBA * SECTOR)
        stage = bytearray(f.read(STAGE_SIZE))
    rec = bytearray(banlz.decompress_all(bytes(stage))[1][1])
    orig_len = len(rec)
    total, flags, at = banlz.parse_header(bytes(stage), SLOT_START)

    n_inplace = n_reloc = n_skip = 0
    for idx in range(142, 212):
        r = rows[idx]
        off, nb = r["offset"], r["nbytes"]
        cur = bytes(rec[off:off + nb]).split(b"\x00")[0].decode("cp932")
        new = transform(idx, cur)
        if new is None:
            n_skip += 1
            continue
        enc = new.encode("cp932")
        if len(enc) <= nb:
            rec[off:off + nb] = enc + b"\x00" * (nb - len(enc))
            n_inplace += 1
        else:
            new_off = len(rec)
            rec += enc + b"\x00"
            cnt = replace_ptr(rec, BASE + off, BASE + new_off)
            assert cnt >= 1, "row %d: no pointer found" % idx
            for x in range(off, off + nb):
                rec[x] = 0
            n_reloc += 1
    print("rows: %d in-place, %d relocated, %d untouched"
          % (n_inplace, n_reloc, n_skip))

    blob = banlz.compress_record(bytes(rec), flags)
    assert banlz.decompress_record(blob)[0] == bytes(rec)
    slot = SLOT_END - SLOT_START
    print("record %d->%d bytes; blob %d / slot %d -> %s"
          % (orig_len, len(rec), len(blob), slot,
             "FITS" if len(blob) <= slot else "TOO BIG"))
    assert len(blob) <= slot
    stage[SLOT_START:SLOT_END] = blob + b"\x00" * (slot - len(blob))
    chk = banlz.decompress_all(bytes(stage))
    assert all(x[1] is not None for x in chk) and chk[1][1] == bytes(rec)
    import banlz_strict as bs
    t2, fl2, at2 = banlz.parse_header(bytes(stage), SLOT_START)
    probs = bs.verify(bytes(stage), at2, t2)[1]
    print("strict problems:", len(probs))
    assert not probs

    shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR)
        f.write(stage)
        # apply both renderer patches to the ELF
        f.seek(ELF_LBA * SECTOR)
        elf = f.read(ELF_SIZE)
        elf = patch_linkpos.apply(elf)
        elf = patch_underline.apply(elf)
        elf = patch_backlog.apply(elf)
        f.seek(ELF_LBA * SECTOR)
        f.write(elf)
    print("wrote", OUT_ISO, "(rec001 corridor polish + linkpos + underline + backlog)")


if __name__ == "__main__":
    main()
