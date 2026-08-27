# How to play it

The patch contains none of the game — you apply it to your own copy.

## Apply it

**Already have a `.iso`?** That is the whole job - a PS2 `.iso` is already the
2048-byte/sector image the patch expects:

```sh
xdelta3 -d -s "Super Robot Taisen Z (Japan).iso" SRWZ-English-v0.8.96.xdelta "SRWZ English.iso"
```

**Have a `.chd`?** Extract it first, then run exactly the same command against
what comes out:

```sh
chdman extractcd -i "Super Robot Taisen Z (Japan).chd" -o tmp.cue -ob game.bin
xdelta3 -d -s game.bin SRWZ-English-v0.8.96.xdelta "SRWZ English.iso"
```

`tmp.cue` and `game.bin` are scratch - delete them afterwards.

Load **`SRWZ English.iso`** in PCSX2 and play. If you would rather have a
smaller file, `chdman createcd -i "SRWZ English.iso" -o "SRWZ English.chd"`
turns it into a CHD, but nothing requires it.

You need [xdelta3](https://github.com/jmacd/xdelta-gpl/releases), and `chdman`
from [MAME](https://www.mamedev.org/) only if your copy is a `.chd`. Neither
ships here.

Prefer clicking to typing? **DeltaPatcher** does the xdelta step for you:
original file `game.bin` (or your `.iso`), patch
`SRWZ-English-v0.8.96.xdelta`, Apply.

## Why not just patch the .chd directly?

Because it would only work for some people, and would fail for everyone else in
a way that looks like a corrupt download.

Two CHDs can hold the same disc **bit for bit** and still be different files.
Rebuilding this game's Japanese CHD with our own `chdman` gave:

    SHA1        1b082c010694f56d9a842276a733a1a9dc1f52d4   identical
    Data SHA1   46ed63ec9d4bfd02e1dc2393a5b86ea4c3206cc6   identical
    file size   2,532,295,277  vs  2,536,283,758           4 MB apart

Same disc, same data, same CHD version, same 19,584-byte hunks, same
`cdlz`/`cdzl`/`cdfl` — only the compressed *representation* differs. A CHD
records no creator version, so there is no way to tell from the file which build
made it, or to warn someone that theirs will not match.

That difference is fatal to a delta, because xdelta compares stored bytes and
almost none of them line up. A patch between two CHDs built the same way is
7.5 MB; the same patch across the two above passed **1.5 GB** and was still
growing.

So the patch targets the uncompressed image, where a byte is a byte, and you
rebuild the CHD locally.

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

- **you pointed it at a `.chd`** — extract it first, as above. This is the most
  common one, and in DeltaPatcher it appears as *"the file is not the right one"*
- it is already patched — start again from your clean copy
- it was ripped at 2352 bytes per sector, so it is not 3,758,358,528 bytes.
  Convert it: `python tools/bin2iso.py yours.bin game.bin`

To check your source (use your own filename):

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
