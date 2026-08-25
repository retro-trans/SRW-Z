# -*- coding: utf-8 -*-
"""PCSX2 texture replacements for the prologue title cards.

These two cards are the one piece of text art that is NOT on the disc in
any form we can reach: the string appears nowhere in cp932 (raw or banlz)
and no wide 8-bit TIM2 holds it - see the 0.8.50 changelog for the full
list of files ruled out.  So they are replaced at the emulator level,
the same mechanism the intermission HD labels already use.

A replacement must carry the EXACT dump filename (the hashes in it are
what PCSX2 matches on) and the dump's own dimensions.  Both cards dump as
1024x512 with a transparent ground, the text sitting left of centre.

Usage: gen_intro_cards.py [outdir]      (default: the replacements folder)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 512
FONT = r"C:\Windows\Fonts\times.ttf"        # serif, like the 明朝 original
SIZE = 34
CENTER_X, TOP = 320, 203                    # measured off the dumps:
                                            # both JP lines centre on x~320
DEST = (r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\replacements")

# dump filename -> (japanese, english)
#
# The SAME card hashes differently on different PCSX2 builds - the user's
# other machine produced 7d47ebcc.../84d6382e... where 2.6.3 here produces
# 3a0907da..., so a name is only valid for the build that dumped it.  Keep
# every known name: extra files cost nothing and the right one wins.
CARDS = {
    "84d6382e3ee8a0af-b6f9a9ca4ec2e23c-00002693.png":
        ("\u305d\u306e\u65e5\u3001\u4e16\u754c\u306f\u5d29\u58ca\u3057\u305f\u2026\u2026",
         "On that day, the world collapsed..."),
    # dumped locally by PCSX2 2.6.3 - the one that actually matches here
    "3a0907da78212f09-b6f9a9ca4ec2e23c-00002693.png":
        ("そして、新しい世界が始まる……",
         "And so, a new world begins..."),
    "7d47ebcc988fa57e-b6f9a9ca4ec2e23c-00002693.png":
        ("\u305d\u3057\u3066\u3001\u65b0\u3057\u3044\u4e16\u754c\u304c\u59cb\u307e\u308b\u2026\u2026",
         "And so, a new world begins..."),
}


def card(text):
    """1024x512 RGBA, transparent, white serif text with a soft shadow."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, SIZE)
    bb = dr.textbbox((0, 0), text, font=font)
    left = CENTER_X - (bb[2] - bb[0]) // 2 - bb[0]
    # shadow first, then the face - the original has a faint dark halo
    for dx, dy in ((1, 1), (2, 2)):
        dr.text((left + dx, TOP + dy), text, font=font, fill=(0, 0, 0, 90))
    dr.text((left, TOP), text, font=font, fill=(255, 255, 255, 255))
    return img


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else DEST
    for name, (jp, en) in CARDS.items():
        path = os.path.join(outdir, name)
        card(en).save(path)
        print("%s\n   %s  ->  %s" % (name, jp, en))
    print("written to %s" % outdir)


if __name__ == "__main__":
    main()
