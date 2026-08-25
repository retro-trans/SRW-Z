# -*- coding: utf-8 -*-
"""Translate the prologue title cards INSIDE the disc (no texture packs).

The cards (その日、世界は崩壊した…… / そして、新しい世界が始まる……)
exist nowhere as text - they are pre-rendered art, like the episode title
cards.  Found via the user's savestate: EE RAM at the moment the card is
shown holds a [0x20 container wrapper][TIM2] record - the SAME wrapper
the VT1 title bank uses - with a LINEAR (unswizzled) 640x448 8-bit image
and a 256-entry CLUT that is a plain 16-step grayscale ramp:
    index k  ->  gray k*16, alpha 0x80   (only indices 0..15 are used)
so painting English means quantising a grayscale render to v // 16.

The records live banlz-compressed in VT1.BIN.  This tool decompresses
each record from the CURRENT iso, verifies it looks like a prologue card
(640x448, type 5, grayscale ramp), blanks the ink band, renders the
English line centred at the same baseline, recompresses, and splices back
into the record's own slot - zero-padded, nothing else moved.

CARDS maps VT1 record offsets to text; fill in offsets from the scanner.

Usage: patch_prologue_cards.py <iso> [--preview DIR] [--revert]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from PIL import Image, ImageDraw, ImageFont

VT1_LBA, SECTOR = 1588772, 2048
W, H = 640, 448
PIXOFF = 0x20 + 16 + 48                  # wrapper + TIM2 magic + pic header
IMGSZ = W * H
FONT = r"C:\Windows\Fonts\yumindb.ttf"   # Yu Mincho Demibold - serif like the JP
FALLBACK = r"C:\Windows\Fonts\times.ttf"
PRISTINE = r"E:\Projects\SRW Z\_work\iso\srwz_alldlg.bin"

# vt1_offset: (japanese, english, point_size)
CARDS = {
    # filled in from the size-based scanner - see the 0.8.53 changelog
}


def load_record(iso, off):
    iso.seek(VT1_LBA * SECTOR + off)
    blob = iso.read(1 << 20)
    dec, used = banlz.decompress_record(blob, 0)
    return bytes(dec), used


def looks_like_card(rec):
    if len(rec) < PIXOFF + IMGSZ + 1024:
        return False
    if rec[0x20:0x24] != b"TIM2":
        return False
    w, h = struct.unpack_from("<HH", rec, 0x20 + 16 + 0x14)
    it = rec[0x20 + 16 + 0x13]
    return (w, h, it) == (W, H, 5)


def render_line(text, pt):
    """Grayscale 640x448 render of one centred line at the JP baseline."""
    K = 4
    img = Image.new("L", (W * K, H * K), 0)
    dr = ImageDraw.Draw(img)
    path = FONT if os.path.exists(FONT) else FALLBACK
    font = ImageFont.truetype(path, pt * K)
    bb = dr.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    # JP ink occupies rows 208..238; centre the En line on the same band
    x = (W * K - tw) // 2 - bb[0]
    y = 223 * K - (bb[1] + bb[3]) // 2
    dr.text((x, y), text, font=font, fill=255)
    return img.resize((W, H), Image.LANCZOS)


def main():
    iso_path = sys.argv[1]
    preview = None
    if "--preview" in sys.argv:
        preview = sys.argv[sys.argv.index("--preview") + 1]
    revert = "--revert" in sys.argv
    assert CARDS, "fill in CARDS with the scanner's VT1 offsets first"
    iso = open(iso_path, "r+b")
    src = open(PRISTINE, "rb") if revert else None
    for off, (jp, en, pt) in sorted(CARDS.items()):
        rec, used = load_record(iso, off)
        assert looks_like_card(rec), "VT1+%#x is not a prologue card" % off
        # slot = up to the next 16-aligned non-zero byte after the blob
        iso.seek(VT1_LBA * SECTOR + off)
        raw = iso.read(1 << 20)
        k = used
        while k < len(raw) and raw[k] == 0:
            k += 1
        slot = k & ~0xF if (k & 0xF) else k
        if revert:
            src.seek(VT1_LBA * SECTOR + off)
            blob = src.read(slot)
            iso.seek(VT1_LBA * SECTOR + off)
            iso.write(blob)
            print("VT1+%#x restored from the pristine image" % off)
            continue
        d = bytearray(rec)
        # blank the ink band completely (rows 200..248 to be safe)
        for y in range(200, 249):
            d[PIXOFF + y * W:PIXOFF + (y + 1) * W] = bytes(W)
        gr = render_line(en, pt).load()
        for y in range(180, 260):
            for x in range(W):
                v = gr[x, y]
                if v >= 8:
                    d[PIXOFF + y * W + x] = min(15, v // 16)
        blob = banlz.compress_record(bytes(d))
        assert len(blob) <= slot, ("VT1+%#x: %d > slot %d" % (off, len(blob), slot))
        rt, _ = banlz.decompress_record(blob, 0)
        assert bytes(rt) == bytes(d), "roundtrip failed at VT1+%#x" % off
        if preview:
            img = Image.new("L", (W, H))
            p = img.load()
            for y in range(H):
                for x in range(W):
                    p[x, y] = min(255, d[PIXOFF + y * W + x] * 16)
            img.save(os.path.join(preview, "card_%x.png" % off))
        else:
            iso.seek(VT1_LBA * SECTOR + off)
            iso.write(blob + b"\x00" * (slot - len(blob)))
        print("VT1+%#x  %s -> %r  (blob %d / slot %d)"
              % (off, jp, en, len(blob), slot))
    iso.close()
    print("preview written" if preview else "done")


if __name__ == "__main__":
    main()
