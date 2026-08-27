# How to play it

The patch contains none of the game — you apply it to your own copy.

## Three commands

```sh
chdman extractcd -i "Super Robot Taisen Z (Japan).chd" -o tmp.cue -ob game.bin

xdelta3 -d -s game.bin SRWZ-English-v0.8.96.xdelta "SRWZ English.iso"

chdman createcd -i "SRWZ English.iso" -o "SRWZ English.chd"
```

Load **`SRWZ English.chd`** in PCSX2 and play. You can delete `game.bin`,
`tmp.cue` and the `.iso` afterwards.

**In a hurry?** Stop after the second command — PCSX2 plays `SRWZ English.iso`
directly. The third command just makes it about a third the size.

**Already have a `.iso` or `.bin`?** Skip the first command and use your file
in place of `game.bin`.

You need [xdelta3](https://github.com/jmacd/xdelta-gpl/releases) and `chdman`
from [MAME](https://www.mamedev.org/). Neither ships here.

Prefer clicking to typing? **DeltaPatcher** does the middle command for you:
original file `game.bin`, patch `SRWZ-English-v0.8.96.xdelta`, Apply.

## Why not just patch the .chd directly?

Because it would only work for some people, and would fail for everyone else in
a way that looks like a corrupt download.

A CHD is compressed in blocks, and two CHDs of the *same disc* contain different
bytes if they were built by different `chdman` versions. We measured it:
rebuilding a Japanese CHD with our own `chdman` produced a file **4 MB
different** from the original, despite identical contents, identical CHD version,
identical 19,584-byte hunks and identical `cdlz`/`cdzl`/`cdfl` compression.

A patch built against one of those CHDs is 7.5 MB; the same patch against the
other passed **1.5 GB** and was still growing. So the patch targets the
uncompressed image, where a byte is a byte, and you rebuild the CHD locally.

## Optional — sharper UI art

`SRWZ-texture-pack.zip` upscales art the game draws as textures. Copy its
`textures` folder into your PCSX2 user directory so you end up with

    <PCSX2 user dir>/textures/SLPS-25887/replacements/*.png

then tick **Settings → Graphics → Texture Replacement → Load Textures** and
restart PCSX2 — it only scans that folder at boot.

Set the upscale multiplier **globally**, not per-game: per-game settings are
keyed to the disc's CRC, so they silently reset every time you update the patch.

## If it does not work

**`target window checksum mismatch: XD3_INVALID_INPUT`**

The file you gave `-s` is not the Japanese original the patch expects. Almost
always one of:

- it is already patched — start again from your clean copy
- it was ripped at 2352 bytes per sector, so it is not 3,758,358,528 bytes.
  Convert it: `python tools/bin2iso.py yours.bin game.bin`

To check:

```sh
sha1sum game.bin                    # Linux / macOS / Git Bash
certutil -hashfile game.bin SHA1    # Windows
```

    before   3,758,358,528 bytes   sha1 e8dbe37e88afe8f82d48889b0775274ccde3cf99
    after    3,758,358,528 bytes   sha1 d1d91523d32d646fbcf97251e39bd5b8f1d2397f

**`using default source filename: game.bin`**

You left out `-s`. The source filename is stored inside the patch, so xdelta
guesses at one and then cannot find it — which reads like a missing-file error
rather than a missing flag.

**`file open failed: read: ...`**

Wrong path. On Windows, quote anything containing spaces.

**It plays, but something looks wrong.**

Please [open an issue](../../issues) with a screenshot. Most of the real bugs in
this project were found by someone playing it and noticing something odd on
screen, not by any automated check.
