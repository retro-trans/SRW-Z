# Applying the patch

The patch is an **xdelta** — a list of differences. It contains none of the
game, so it is useless on its own: you apply it to your own dump of the
Japanese disc and get a playable English image.

Everything below is one command per step. If something goes wrong, the
[Troubleshooting](#troubleshooting) section has the actual error messages and
what each one means.

## What you need

| | |
|---|---|
| Your own copy of **Super Robot Taisen Z** (PS2, SLPS-25887), dumped | — |
| `SRWZ-English-v0.8.96.xdelta` | from the [latest release](../../releases/latest) |
| **xdelta3** | <https://github.com/jmacd/xdelta-gpl/releases> |
| **chdman** *(only if your dump is a `.chd`, or you want one at the end)* | from [MAME](https://www.mamedev.org/) |

Neither tool ships here — get them from their own projects.

## Step 1 — get a raw 2048-byte/sector image

The patch expects a plain `MODE1/2048` image, 3,758,358,528 bytes. Which
command you need depends on what you have:

**If you have a `.chd`:**

```sh
chdman extractcd -i "Super Robot Taisen Z (Japan).chd" -o srwz.cue -ob srwz.bin
```

**If you have a `.bin`/`.cue` ripped at 2352 bytes per sector** (its `.cue` says
`MODE1/2352`), convert it:

```sh
python tools/bin2iso.py srwz_2352.bin srwz.bin
```

**If you already have a `.iso`**, it is almost certainly 2048 already — just
rename it to `srwz.bin`, or pass the `.iso` name to Step 3.

## Step 2 — check you have the right source

This is worth 30 seconds. A source that differs by one byte fails in Step 3
with a message that does not say which byte.

```sh
sha1sum srwz.bin        # Linux / macOS / Git Bash
certutil -hashfile srwz.bin SHA1     # Windows cmd
```

    size   3,758,358,528 bytes
    sha1   e8dbe37e88afe8f82d48889b0775274ccde3cf99

A different hash does **not** mean your disc is wrong — it usually means the
image was ripped at 2352 bytes per sector (go back to Step 1) or the dump
includes subchannel data. The size is the quickest tell: if it is not exactly
3,758,358,528, it is not the right shape yet.

## Step 3 — apply the patch

```sh
xdelta3 -d -s srwz.bin SRWZ-English-v0.8.96.xdelta srwz-en.bin
```

`-d` decodes, `-s` names the source. It takes a few minutes and prints nothing
on success.

Prefer a GUI? **DeltaPatcher** does the same thing: original file `srwz.bin`,
xdelta `SRWZ-English-v0.8.96.xdelta`, then Apply patch.

## Step 4 — check the result

```sh
sha1sum srwz-en.bin
```

    size   3,758,358,528 bytes
    sha1   d1d91523d32d646fbcf97251e39bd5b8f1d2397f

If that matches, the patch applied exactly and the rest is emulator setup.

## Step 5 — play it

**Straight from the image.** PCSX2 will boot `srwz-en.bin` as-is:

```sh
pcsx2-qt -- srwz-en.bin
```

**Or build a CHD**, which is a third the size. Save this as `srwz-en.cue`
beside the image:

```
FILE "srwz-en.bin" BINARY
  TRACK 01 MODE1/2048
    INDEX 01 00:00:00
```

then:

```sh
chdman createcd -i srwz-en.cue -o srwz-en.chd
```

## Optional: the texture pack

`SRWZ-texture-pack.zip` sharpens UI art that the game draws as textures rather
than text. Copy its `textures` folder into your PCSX2 user directory so you get

    <PCSX2 user dir>/textures/SLPS-25887/replacements/*.png

then turn on **Settings → Graphics → Texture Replacement → Load Textures** and
restart. PCSX2 only scans that folder at boot.

It is keyed by game serial, not by CRC, so it keeps working across patch
versions. Per-game *settings* are the opposite — they are keyed by CRC, so a
per-game upscale setting silently reverts every time you update the patch. Set
the upscale multiplier globally instead.

## Troubleshooting

**`target window checksum mismatch: XD3_INVALID_INPUT`**

```
xdelta3: target window checksum mismatch: XD3_INVALID_INPUT
xdelta3: normally this indicates that the source file is incorrect
xdelta3: please verify the source file with sha1sum or equivalent
```

Your `srwz.bin` is not the image the patch was built against. Re-check Step 2.
The usual cause is a 2352-byte-per-sector rip; the second most common is
patching an already-patched image.

**`using default source filename: srwz.bin`**

You left out `-s`. The source filename is stored inside the patch, so xdelta
guesses — and fails if no file of that name is beside it. Pass `-s` explicitly.

**`file open failed: read: ...`**

The path is wrong. On Windows, quote any path containing spaces:
`-s "C:\games\Super Robot Taisen Z (Japan).bin"`.

**It applied, but the hash in Step 4 does not match.**

Do not play it. Re-run Step 2 on the source: if the source hash was right and
the output is wrong, the patch file itself is damaged — download it again.

**The game boots but text is garbled or it freezes on loading a save.**

That is not a patching problem — please [open an issue](../../issues) with a
screenshot and the hash from Step 4. A screenshot is worth more than a
description; most real bugs in this project were found by someone noticing
something odd on screen.
