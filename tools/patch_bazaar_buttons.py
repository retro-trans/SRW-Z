# -*- coding: utf-8 -*-
"""Paint "Buy"/"Sell" over the bazaar 購入/売却 button glyphs.

The bazaar buttons are TEXTURE ART, not strings: a 4bpp TIM2 word sheet
inside KVMDATA.BIN (file offset 0x28B40, ISO offset 0x9D751B40 in the
current layout - located by save-stating on the bazaar screen and tracing
the EE-RAM copy at 0xC5A9A0 back to disc; pixel data matched byte-for-byte,
only the CLUT differs at runtime because the game palette-animates it).

Sheet layout (256x256, 128 bytes/row): 購入 occupies rows 96-127, 売却
rows 128-159, both x 0-63. The button blits those sub-rects. We re-render
"Buy"/"Sell" in Georgia Bold using the same palette indices the Japanese
glyphs use: 15 = fill, 11 = anti-alias edge, 4 = drop shadow, 0 = clear.
CLUT indices, not colors, so the runtime palette animation keeps working.

Usage: patch_bazaar_buttons.py <iso> [--revert]
Idempotent: verifies the block holds either the JP original or our EN
version before writing.
"""
import hashlib
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

KVMDATA_LBA = 1289810
TEX_OFF_IN_FILE = 0x28B40          # TIM2 header start inside KVMDATA.BIN
SECTOR = 2048
ROWBYTES = 128                     # 256px at 4bpp
FILL, EDGE, SHADOW, CLEAR = 15, 11, 4, 0
FONT = r"C:\Windows\Fonts\georgiab.ttf"

BOXES = [("Buy", 96), ("Sell", 128)]   # (label, first row); both x0-63, 32 rows


def render_label(text, w=64, h=32):
    """Return an index-map (w*h list) for the label in the JP glyph style."""
    big = 4                            # supersample for clean AA
    img = Image.new("L", (w * big, h * big), 0)
    draw = ImageDraw.Draw(img)
    size = 26 * big
    font = ImageFont.truetype(FONT, size)
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    while tw > (w - 4) * big:
        size -= big
        font = ImageFont.truetype(FONT, size)
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = (w * big - tw) // 2 - bb[0]
    y = (h * big - th) // 2 - bb[1]
    draw.text((x, y), text, fill=255, font=font)
    small = img.resize((w, h), Image.LANCZOS)
    a = small.load()
    out = [CLEAR] * (w * h)
    # drop shadow first (offset +2,+2 like the JP glyphs), then fill/edge
    for yy in range(h):
        for xx in range(w):
            if a[xx, yy] >= 128 and xx + 2 < w and yy + 2 < h:
                out[(yy + 2) * w + (xx + 2)] = SHADOW
    for yy in range(h):
        for xx in range(w):
            v = a[xx, yy]
            if v >= 160:
                out[yy * w + xx] = FILL
            elif v >= 56:
                out[yy * w + xx] = EDGE
    return out


def main():
    iso_path = sys.argv[1]
    revert = "--revert" in sys.argv
    tex_start = KVMDATA_LBA * SECTOR + TEX_OFF_IN_FILE
    with open(iso_path, "r+b") as iso:
        iso.seek(tex_start)
        hdr = iso.read(52)
        assert hdr[:4] == b"TIM2", "no TIM2 at expected offset - layout moved?"
        tot, clutsz, imgsz, hdrsz, clutcol = struct.unpack_from("<IIIHH", hdr, 16)
        w, h = struct.unpack_from("<HH", hdr, 36)
        assert (w, h, imgsz) == (256, 256, 32768), "unexpected texture shape"
        pix_start = tex_start + 16 + hdrsz

        # original JP glyph block (rows 96-160), for verify/revert
        iso.seek(pix_start + 96 * ROWBYTES)
        cur = bytearray(iso.read(64 * ROWBYTES))
        orig_path = r"E:\Projects\SRW Z\_work\analysis\bazaar\jp_buttons_block.bin"
        try:
            orig = open(orig_path, "rb").read()
        except FileNotFoundError:
            orig = None

        if revert:
            assert orig, "no saved original block to revert to"
            iso.seek(pix_start + 96 * ROWBYTES)
            iso.write(orig)
            print("reverted to JP glyphs")
            return

        if orig is None:
            open(orig_path, "wb").write(bytes(cur))
            print("saved JP original block (%d bytes)" % len(cur))

        for text, row0 in BOXES:
            m = render_label(text)
            for yy in range(32):
                for xx in range(0, 64, 2):
                    lo = m[yy * 64 + xx]
                    hi = m[yy * 64 + xx + 1]
                    cur[(row0 - 96 + yy) * ROWBYTES + xx // 2] = lo | (hi << 4)
        iso.seek(pix_start + 96 * ROWBYTES)
        iso.write(bytes(cur))
        print("painted Buy/Sell at rows 96-159 (sha1 %s)"
              % hashlib.sha1(bytes(cur)).hexdigest()[:12])

        # preview PNG of the edited region
        iso.seek(pix_start)
        pix = iso.read(imgsz)
        iso.seek(pix_start + imgsz)
        clut = iso.read(clutsz)
        pal = [(clut[c*4], clut[c*4+1], clut[c*4+2], min(255, clut[c*4+3]*2))
               for c in range(clutsz // 4)]
        img = Image.new("RGBA", (256, 256))
        px = []
        for b0 in pix:
            px.append(pal[b0 & 0xF]); px.append(pal[b0 >> 4])
        img.putdata(px)
        img.crop((0, 88, 128, 168)).resize((512, 320), Image.NEAREST).save(
            r"E:\Projects\SRW Z\_work\analysis\bazaar\preview_buttons.png")
        print("preview: analysis/bazaar/preview_buttons.png")


if __name__ == "__main__":
    main()
