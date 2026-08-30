# -*- coding: utf-8 -*-
"""Convert PCSX2 captures to a resolution romhacking.net will accept.

RHDN rejects any screenshot whose pixel size is not a native mode for the
platform, and a windowed PCSX2 capture never is - the five submitted for SRW Z
came out 917x690 / 920x690 / 922x690 and were all refused.

Two things this does that a blind resize does not:

  * TRIMS uniform black borders first. PCSX2 letterboxes when the window
    aspect does not match the game's, so the capture carries bars that are not
    part of the image. Resizing without trimming squashes the picture to fit
    bars that should not be there.
  * picks the native mode CLOSEST IN ASPECT to the trimmed image, preferring a
    real PS2 mode over the PC sizes that also appear on RHDN's list. SRW Z's
    screens are not all one shape: the dialogue scenes come out 4:3 and map to
    640x480, while the unit status screen is 1.42 and maps to 640x448.
      Forcing everything to one size would distort one of the two.

Accepted sizes are RHDN's own list, quoted from its rejection message.

Usage: rhdn_screenshots.py <out-dir> <image> [image ...]
"""
import os
import sys

from PIL import Image, ImageChops

# RHDN's list. The 640x* modes and 720x480 are genuine PS2 output; the rest are
# PC/HD sizes that the same list happens to allow.
ACCEPTED = [(640, 240), (640, 224), (640, 480), (640, 448), (640, 288),
            (640, 256), (640, 576), (640, 512), (800, 600), (1024, 768),
            (1280, 1024), (720, 480), (1920, 1080), (1280, 720)]
NATIVE_PS2 = {(640, 240), (640, 224), (640, 480), (640, 448), (640, 288),
              (640, 256), (640, 576), (640, 512), (720, 480)}


def trim_black(im):
    """Drop uniform black bars. Returns (image, description)."""
    rgb = im.convert("RGB")
    bg = Image.new("RGB", rgb.size, (0, 0, 0))
    box = ImageChops.difference(rgb, bg).getbbox()
    if not box or box == (0, 0, rgb.width, rgb.height):
        return im, ""
    cut = im.crop(box)
    return cut, " trimmed %dx%d->%dx%d" % (im.width, im.height,
                                           cut.width, cut.height)


def best_size(w, h):
    ar = w / float(h)
    def rank(c):
        err = abs((c[0] / float(c[1])) - ar)
        return (round(err, 4), 0 if c in NATIVE_PS2 else 1,
                abs(c[0] * c[1] - w * h))
    return min(ACCEPTED, key=rank)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out = sys.argv[1]
    if not os.path.isdir(out):
        os.makedirs(out)
    for n, src in enumerate(sys.argv[2:], 1):
        im = Image.open(src)
        before = "%dx%d" % (im.width, im.height)
        im, note = trim_black(im)
        size = best_size(im.width, im.height)
        res = im.convert("RGB").resize(size, Image.LANCZOS)
        name = "%02d-%s.png" % (n, os.path.splitext(os.path.basename(src))[0])
        res.save(os.path.join(out, name))
        print("  %-34s %-9s -> %dx%d%s"
              % (os.path.basename(src), before, size[0], size[1], note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
