# How to play it

The patch contains none of the game — you apply it to your own copy.

## Two commands

If you have the Japanese game as a `.chd`:

```sh
chdman extractcd -i "Super Robot Taisen Z (Japan).chd" -o game.cue -ob game-jp.bin

xdelta3 -d -s game-jp.bin SRWZ-English-v0.8.96.xdelta "SRWZ English.bin"
```

That is it. Drag **`SRWZ English.bin`** into PCSX2 and play.

If your copy is already a `.iso` or `.bin`, skip the first command and use your
file in place of `game-jp.bin`.

You need [xdelta3](https://github.com/jmacd/xdelta-gpl/releases) and, for the
first command only, `chdman` from [MAME](https://www.mamedev.org/). Neither
ships here.

Prefer clicking to typing? **DeltaPatcher** does the second command for you:
original file `game-jp.bin`, patch `SRWZ-English-v0.8.96.xdelta`, Apply.

## Optional — make a .chd

A CHD is about a third the size. Save this as `en.cue` next to the patched file:

```
FILE "SRWZ English.bin" BINARY
  TRACK 01 MODE1/2048
    INDEX 01 00:00:00
```

then:

```sh
chdman createcd -i en.cue -o "SRWZ English.chd"
```

**Do not** expect an xdelta built for a `.chd` to work. A CHD compresses in
blocks, and two copies of the *same* disc compress to different bytes if they
were made by different `chdman` builds — we measured a 4 MB size difference
between two CHDs of identical content. That is why the patch targets the
uncompressed image: built against a CHD it came out over 1.5 GB, against the
image it is 6 MB.

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

The file you pointed `-s` at is not the Japanese original the patch expects.
Almost always one of:

- it is an already-patched image (start again from your clean copy)
- it was ripped at 2352 bytes per sector — the file will not be
  3,758,358,528 bytes. Convert it: `python tools/bin2iso.py yours.bin game-jp.bin`

To check your copy is the right one:

```sh
sha1sum game-jp.bin                    # Linux / macOS / Git Bash
certutil -hashfile game-jp.bin SHA1    # Windows
```

    3,758,358,528 bytes    sha1 e8dbe37e88afe8f82d48889b0775274ccde3cf99

and the patched result should be:

    3,758,358,528 bytes    sha1 d1d91523d32d646fbcf97251e39bd5b8f1d2397f

**`using default source filename: game-jp.bin`**

You left out `-s`. The source filename is stored inside the patch, so xdelta
guesses at one and then cannot find it — which looks like a missing-file error
rather than a missing flag.

**`file open failed: read: ...`**

Wrong path. On Windows, put quotes around anything containing spaces.

**It plays, but something looks wrong.**

Please [open an issue](../../issues) with a screenshot. Most of the real bugs
in this project were found by someone playing it and noticing something odd on
screen, not by any automated check.
