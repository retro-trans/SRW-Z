# Super Robot Taisen Z — translation project

An open toolchain for translating **Super Robot Taisen Z** (PlayStation 2,
SLPS-25887), plus the English translation built with it.

## Play it

Get `SRWZ-English-v0.8.96.xdelta` from the
[latest release](../../releases/latest). You need your own copy of the game.

**If you have a `.iso`** - one command:

```sh
xdelta3 -d -s "Super Robot Taisen Z (Japan).iso" SRWZ-English-v0.8.96.xdelta "SRWZ English.iso"
```

**If you have a `.chd`** - extract it first, then the same command:

```sh
chdman extractcd -i "Super Robot Taisen Z (Japan).chd" -o tmp.cue -ob game.bin
xdelta3 -d -s game.bin SRWZ-English-v0.8.96.xdelta "SRWZ English.iso"
```

You need [xdelta3](https://github.com/jmacd/xdelta-gpl/releases), and `chdman`
from [MAME](https://www.mamedev.org/) only if your copy is a `.chd`. Neither
ships here. Prefer clicking? **DeltaPatcher** does the xdelta step for you.

### Sharper UI art (optional)

`SRWZ-texture-pack.zip` upscales art the game draws as textures. Copy its
`textures` folder into your PCSX2 user directory, giving
`textures/SLPS-25887/replacements/*.png`, then tick **Settings -> Graphics ->
Texture Replacement -> Load Textures** and restart - PCSX2 only scans that
folder at boot. Set the upscale multiplier **globally**, not per-game:
per-game settings are keyed to the disc CRC and silently reset on every patch
update.

## Translate it

Fork it to fix the English, or to take the game into another language. Start
with **[TRANSLATING.md](TRANSLATING.md)**.

```sh
python tools/extract_script.py mygame.bin script.json   # pull the text out
#   ... edit the "text" fields ...
python tools/apply_script.py mygame.bin script.json --write
python tools/verify_pointers.py mygame.bin --min 85     # never skip this
```

Round-trip is exact by construction: extract, change nothing, apply, and the
image is byte-identical.

You need your own copy of the game. This repository contains no disc image, no
game data and no dump of the original Japanese script — `extract_script.py`
reads those from the disc you dump yourself.

## Check the translation

Judge it for yourself - one command, and only your own japanese disc:

```sh
python tools/compare_translation.py "Super Robot Taisen Z (Japan).chd"
```

Writes an HTML page with the Japanese beside our English, filterable by
record and searchable in either language. No patched image needed.
Details, and how to change a line, are in
**[TRANSLATING.md](TRANSLATING.md)**.

## What is here

| Path | Contents |
|---|---|
| `TRANSLATING.md` | **start here** — the edit loop and the rules the engine enforces |
| `TOOLS.md` | every tool, what it is for, and when you need it |
| `tools/` | 158 tools: the LZ codec, the pipeline, patchers, verifiers, gates |
| `analysis/english_script.json` | the English translation — 167,613 strings |
| `analysis/translation_pairs.json` | our English keyed by Japanese offset, for the check above |
| `analysis/glossary.json` | 1000 terms, with provenance in `glossary_sources.json` |
| `docs/TECHNICAL.md` | how the data, the engine and the pipeline actually work |
| `docs/BASE_RULES.md` | portable rules for running a project like this |
| `docs/RENDERER.md` `VWF.md` `CUSTOM_FONT.md` | how the text engine draws, and the font work |
| `docs/LZ_FORMAT.md` `DEBUGGER_TRACE.md` `FINDINGS.md` | the container format and the live-tracing method |
| `CHANGELOG.md` | every build, what changed, and what broke |

## Using these tools

They expect a decrypted PS2 disc image you dump yourself from your own copy.
Most take the image as their first argument and are read-only unless passed
`--write`:

```sh
python tools/scan_visible_defects.py <iso>          # report
python tools/verify_pointers.py <iso> --min 85      # gate before building
python tools/fix_terms_global.py <iso> --write      # apply
```

Windows note: anything using `multiprocessing` must be a real file on disk, never
a heredoc — spawned workers re-import the module and cannot import `<stdin>`.

## Status

The translation is in progress. `CHANGELOG.md` is the honest record, including
the builds that shipped broken and why.
