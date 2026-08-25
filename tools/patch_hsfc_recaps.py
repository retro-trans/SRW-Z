# -*- coding: utf-8 -*-
"""Translate the episode-recap bank shown on the save/load screen.

HSFC.BIN (LBA 1568541) rec0 (first banlz record, dec 31392 bytes) holds
208 fixed slots of 150 bytes from payload offset 0xB6: three lines of
(48 data bytes + 2 NUL). The save screen's Info panel reads the recap for
the save's episode from here. Escaped every text search for days because
needles spanned the 48-byte line breaks.

Translations: analysis/hsfc_recaps_en.json, keyed by the slot id of the
FIRST slot holding each unique JP text (analysis/hsfc_uniq_jp.json);
duplicate slots (route variants) reuse the same EN. Lines wrapped at 48
ASCII chars, max 3 lines (the panel renders ASCII fine - the EN episode
title in the same panel proves it).

Usage: patch_hsfc_recaps.py <iso>   (idempotent: rebuilds rec0 from the
pristine JP copy in iso/srwz_alldlg.bin every run, then applies EN)
"""
import json
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")
import banlz

WORK = r"E:\Projects\SRW Z\_work"
HSFC_LBA, SECTOR = 1568541, 2048
BASE = 0xB6
SLOT = 150
NLINES, LINEW = 3, 48


def units(w):
    return sum(1.35 if ord(c) > 0x7F else 1 for c in w)


LINE_UNITS = 30            # panel shows ~30 ASCII columns (JP: 24 cells)


def wrap_panel(text):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if units(cand) <= LINE_UNITS:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    assert len(lines) <= NLINES, (len(lines), text)
    return lines


# the panel uses the caption-family renderer: ASCII 0x2D-0x3D are CONTROL
# codes (a bare "." line-feeds mid-panel - seen live). Map them fullwidth;
# "," (0x2C) is a control in the caption engine too.
def enc_line(line):
    out = bytearray()
    for c in line:
        o = ord(c)
        if c == ".":
            out += bytes([0x81, 0x44])
        elif c == ",":
            out += bytes([0x81, 0x43])
        elif c == "-":
            out += bytes([0x81, 0x7C])
        elif c == ":":
            out += bytes([0x81, 0x46])
        elif "0" <= c <= "9":
            out += bytes([0x82, 0x4F + o - 0x30])
        elif o < 0x80:
            out += bytes([o])
        else:
            out += c.encode("cp932")
    assert len(out) <= 48, (len(out), line)
    return bytes(out)


def main():
    iso_path = sys.argv[1]
    en = json.load(open(WORK + r"\analysis\hsfc_recaps_en.json", encoding="utf-8"))
    with open(WORK + r"\iso\srwz_alldlg.bin", "rb") as orig:
        orig.seek(HSFC_LBA * SECTOR)
        raw = orig.read(250112)
    recs = banlz.decompress_all(raw)
    d = bytearray(recs[0][1])
    slot0_of = {}          # JP text -> first slot id
    jp_of = {}
    n_slots = (len(d) - BASE) // SLOT
    for k in range(n_slots):
        off = BASE + k * SLOT
        lines = []
        for li in range(NLINES):
            line = bytes(d[off + li * 50:off + li * 50 + 48]).split(b"\x00")[0]
            if line:
                lines.append(line.decode("cp932"))
        txt = "".join(lines).replace("\u3000", "")
        if not txt:
            continue
        jp_of[k] = txt
        slot0_of.setdefault(txt, k)
    n = 0
    for k, txt in jp_of.items():
        key = str(slot0_of[txt])
        if key not in en:
            print("NO TRANSLATION for slot", k, "->", key)
            continue
        lines = wrap_panel(en[key])
        off = BASE + k * SLOT
        d[off:off + SLOT] = b"\x00" * SLOT
        for li, line in enumerate(lines):
            enc = enc_line(line)
            d[off + li * 50:off + li * 50 + len(enc)] = enc
        n += 1
    # recompress into the original slot (rec1 starts where rec0's stream ended)
    slot_end = recs[1][0]
    blob = banlz.compress_record(bytes(d), None)
    if len(blob) > slot_end:
        blob = banlz.compress_record_optimal(bytes(d), None)
    assert len(blob) <= slot_end, (len(blob), slot_end)
    rt, _ = banlz.decompress_record(blob, 0)
    assert bytes(rt) == bytes(d)
    with open(iso_path, "r+b") as iso:
        iso.seek(HSFC_LBA * SECTOR)
        iso.write(blob + b"\x00" * (slot_end - len(blob)))
    print("recaps translated: %d slots (blob %d/%d)" % (n, len(blob), slot_end))


if __name__ == "__main__":
    main()
