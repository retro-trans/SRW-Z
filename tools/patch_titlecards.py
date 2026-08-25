# -*- coding: utf-8 -*-
"""Repaint the chapter TITLE CARD textures in English.

The 第N話 title cards are pre-rendered art, not text: VT1.BIN holds a bank
of 107 banlz records (true 16-aligned offsets in analysis/vt1_bank_true.json,
first at 0xBA8500), one per episode title, in the SAME ORDER as the
episode-title table at COMPDATA+0x72DA0. Each record decompresses to 16608 bytes:
[0x20 container wrapper][512x64 4bpp TIM2, 48-byte pic header, 16384 px,
128-byte CLUT]. The CLUT is a plain 16-step grayscale ramp with index 0
transparent - the texture is an antialiased luminance mask, so an English
repaint is just: render text, quantize luminance to indices 1-15.

Found via PCSX2 write-breakpoint -> froze inside the banlz decompressor
(0x1C6D70); decompress worker thread reads src/dst from 0x46F650/0x46F658.

English titles come from analysis/title_list_en.json (the translated
COMPDATA table). Records start 16-BYTE ALIGNED (analysis/vt1_bank_true.json);
the first bank scan mistook each slot's leading zero pad for record start,
so two builds painted streams up to 12 bytes early and the game - which
seeks to the aligned offsets - decoded mid-stream noise. Painting now
always restores the PRISTINE bank from iso/srwz_alldlg.bin first, then
splices each English stream at its true offset, zero-padding the tail
(plain compress_record only: the construct set proven in-game by the
dialogue restoration; no exact-size tricks needed - slots are indexed,
not streamed sequentially).

Usage: patch_titlecards.py <iso>   (idempotent - every slot is verified to
hold a wrapper+TIM2 record before writing, JP or EN alike)
"""
import json
import struct
import sys

sys.path.insert(0, r"E:\Projects\SRW Z\_work\tools")
import banlz
from PIL import Image, ImageDraw, ImageFont

WORK = r"E:\Projects\SRW Z\_work"
VT1_LBA, SECTOR = 1588772, 2048
W, H = 512, 64
PIXOFF = 0x20 + 16 + 48            # wrapper + TIM2 magic header + pic header
IMGSZ = W * H // 2                 # 16384
FONT = r"C:\Windows\Fonts\georgiab.ttf"
FLAGS = 0x0F
WRAP12 = bytes.fromhex("010000002000000000000000")



def pack_literals_exact(chunk, budget):
    """Encode chunk as pure literal groups consuming EXACTLY budget bytes.
    Intermediate group: T(lit) + varint nref=0 + lit bytes  -> cost lit+2.
    Final group: T(lit | nref-nibble) + lit bytes -> cost lit+1 (the decoder
    stops at total before reading the refs)."""
    K = len(chunk)
    if K < 1:
        return None
    # cost = K + 2g - 1 for g groups (1..15 bytes each)
    if (budget - K + 1) % 2:
        return None
    g = (budget - K + 1) // 2
    import math
    if not (max(1, (K + 14) // 15) <= g <= K):
        return None
    sizes = []
    rem = K
    for gi in range(g):
        left = g - gi - 1
        s = min(15, rem - left)
        if s < 1:
            return None
        sizes.append(s)
        rem -= s
    if rem != 0:
        return None
    out = bytearray()
    pos = 0
    for gi, s in enumerate(sizes):
        last = gi == len(sizes) - 1
        if last:
            out.append(0x10 | s)          # nref=1, never consumed
            out += chunk[pos:pos + s]
        else:
            out.append(s)                 # nref=0 -> varint follows
            out += banlz._emit_varint(0)
            out += chunk[pos:pos + s]
        pos += s
    assert len(out) == budget, (len(out), budget)
    return bytes(out)


def compress_exact(data, flags, target):
    """banlz record of EXACTLY target bytes (the title loader streams
    records back-to-back, so the next record is found where this stream
    ends - a shorter stream derails every following texture, which is how
    the first painted build corrupted the cards in-game)."""
    window = 1 << (((flags >> 1) & 0xF) + 8)
    head = bytearray()
    head += banlz._emit_varint(len(data))
    head += banlz._emit_varint(flags)
    if not (window >= len(data) and (flags & 0x21) == 1):
        if flags & 0x40:
            head += banlz._emit_varint(0)
    head += banlz._emit_varint(0)
    whole = banlz.compress_record(data, flags)
    if len(whole) == target:
        return whole
    if len(whole) > target:
        return None                       # caller degrades rendering first
    for K in range(1, 4000):
        prefix = banlz.compress_stream(data[:-K], window)
        room = target - len(head) - len(prefix)
        if room < K + 1:
            continue
        tail = pack_literals_exact(data[-K:], room)
        if tail is None:
            continue
        blob = bytes(head) + prefix + tail
        assert len(blob) == target
        # the greedy encoder's FINAL group may rely on the early total-break
        # and omit its nref varint - invalid once our tail follows. Validate
        # the composite and try the next split point if it misparses.
        try:
            rt, used = banlz.decompress_record(blob, 0)
        except Exception:
            continue
        if rt is None or bytes(rt) != bytes(data) or used != target:
            continue
        return blob
    return None


def norm_title(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:          # fullwidth ASCII forms
            ch = chr(o - 0xFEE0)
        elif ch == u"\u2026":
            ch = "..."
        elif ch == u"\u3000":
            ch = " "
        out.append(ch)
    return "".join(out)


def render_title(text, size=32, levels=5):
    """512x64 index map (bytes, one index per pixel), grayscale-AA style.

    levels: number of distinct gray steps INCLUDING transparent 0. Fewer
    levels -> longer byte runs -> smaller banlz stream. Full 16-level AA
    compressed WORSE than the kanji art (2609 vs 1776-byte slot for rec0);
    5 levels is visually identical at this size and compresses far better.
    """
    big = 4
    BASELINE_ROW = 26            # JP kanji ink spans rows 4..27; the ticker
    while size >= 18:            # samples that band, so anchor - not center
        font = ImageFont.truetype(FONT, size * big)
        img = Image.new("L", (W * big, H * big), 0)
        dr = ImageDraw.Draw(img)
        bb = dr.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= (W - 12) * big:
            break
        size -= 2
    ascent, descent = font.getmetrics()
    x = (W * big - tw) // 2 - bb[0]
    y = BASELINE_ROW * big - ascent
    dr.text((x, y), text, fill=255, font=font)
    small = img.resize((W, H), Image.LANCZOS)
    px = small.load()
    out = bytearray(W * H)
    q = levels - 1
    for yy in range(H):
        for xx in range(W):
            step = (px[xx, yy] * q + 127) // 255      # 0..q
            out[yy * W + xx] = (step * 15 + q // 2) // q if step else 0
    return bytes(out)


def main():
    iso_path = sys.argv[1]
    bank = json.load(open(WORK + r"\analysis\vt1_bank_true.json"))
    titles = json.load(open(WORK + r"\analysis\title_list_en.json",
                            encoding="utf-8"))
    assert len(bank) == 107 and len(titles) >= 107
    base = VT1_LBA * SECTOR
    # 16 bytes of margin: earlier bad builds overwrote rec0's leading pad
    region_lo = (bank[0][0] - 16) & ~15
    region_hi = (bank[-1][1] + 3) & ~3
    # always start from the pristine JP bank - self-heals any earlier paint
    with open(WORK + r"\iso\srwz_alldlg.bin", "rb") as orig:
        orig.seek(base + region_lo)
        region = bytearray(orig.read(region_hi - region_lo))
    n_ok = n_shrunk = 0
    for k, (off, end) in enumerate(bank):
        slot = (bank[k + 1][0] - off) if k + 1 < len(bank) \
            else (region_hi - off)
        cur = region[off - region_lo:off - region_lo + slot]
        dec, _ = banlz.decompress_record(cur, 0)
        assert dec and bytes(dec[:12]) == WRAP12 and len(dec) == 16608, \
            "rec%d: pristine slot does not hold a title record" % k
        text = norm_title(titles[k])
        rec = bytearray(dec)
        blob = None
        # degrade gracefully: fewer AA levels first (invisible), then font size
        for size, levels in ((32, 5), (32, 4), (32, 3), (30, 3), (28, 3),
                             (26, 2), (24, 2)):
            pix = render_title(text, size, levels)
            for i in range(0, W * H, 2):
                rec[PIXOFF + i // 2] = pix[i] | (pix[i + 1] << 4)
            blob = banlz.compress_record(bytes(rec), FLAGS)
            if len(blob) <= slot:
                break
            n_shrunk += 1
        assert blob is not None and len(blob) <= slot, \
            "rec%d (%r) cannot fit slot %d (best %d)" % (k, text, slot, len(blob))
        rt, _ = banlz.decompress_record(blob, 0)
        assert bytes(rt) == bytes(rec), "roundtrip failed rec%d" % k
        region[off - region_lo:off - region_lo + slot] =             blob + b"\x00" * (slot - len(blob))
        n_ok += 1
        if k % 20 == 0:
            print("rec%03d %r ok (blob %d/%d)" % (k, text, len(blob), slot))
    with open(iso_path, "r+b") as iso:
        iso.seek(base + region_lo)
        iso.write(bytes(region))
    print("done: %d records painted, %d needed shrink" % (n_ok, n_shrunk))


if __name__ == "__main__":
    main()
