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

Either way, load **`SRWZ English.iso`** in PCSX2 and play.

**A `.chd` cannot be patched directly.** It is compressed, so a patcher sees
none of the bytes it expects - that is what *"the file is not the right one"*
means in DeltaPatcher. Extract it first, as above. Two CHDs can hold the same disc
**bit for bit** and still be different files - rebuilding this game's Japanese
CHD gave an identical `Data SHA1` in a file 4 MB different in size, because a
CHD records only the compressed *representation*. A patch built against one
such CHD is 7.5 MB; against the other it passed 1.5 GB and was still growing.

You need [xdelta3](https://github.com/jmacd/xdelta-gpl/releases), and `chdman`
from [MAME](https://www.mamedev.org/) only if your copy is a `.chd`. Neither
ships here. Prefer clicking? **DeltaPatcher** does the xdelta step for you.

### If it does not work

`target window checksum mismatch: XD3_INVALID_INPUT` means the file you gave
`-s` is not the Japanese original. Almost always one of:

- **you pointed it at a `.chd`** - extract it first. In DeltaPatcher this shows
  as *"the file is not the right one"*
- it is already patched - start again from a clean copy
- it was ripped at 2352 bytes per sector, so it is not 3,758,358,528 bytes.
  Convert it with `python tools/bin2iso.py yours.bin game.bin`

`using default source filename:` means you left out `-s`. The source name is
stored inside the patch, so xdelta guesses at one and then cannot find it.

To check a file (use your own filename):

```sh
sha1sum game.bin                    # Linux / macOS / Git Bash
certutil -hashfile game.bin SHA1    # Windows
```

```
before   3,758,358,528 bytes   sha1 e8dbe37e88afe8f82d48889b0775274ccde3cf99
after    3,758,358,528 bytes   sha1 d1d91523d32d646fbcf97251e39bd5b8f1d2397f
```

If it plays but something looks wrong, please [open an issue](../../issues)
with a screenshot - most real bugs here were found that way, not by any
automated check.

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

## What is here

| Path | Contents |
|---|---|
| `TRANSLATING.md` | **start here** — the edit loop and the rules the engine enforces |
| `TOOLS.md` | every tool, what it is for, and when you need it |
| `tools/` | 158 tools: the LZ codec, the pipeline, patchers, verifiers, gates |
| `analysis/english_script.json` | the English translation — 167,613 strings |
| `analysis/glossary.json` | 1000 terms, with provenance in `glossary_sources.json` |
| `docs/TECHNICAL.md` | how the data, the engine and the pipeline actually work |
| `docs/BASE_RULES.md` | portable rules for running a project like this |
| `docs/RENDERER.md` `VWF.md` `CUSTOM_FONT.md` | how the text engine draws, and the font work |
| `docs/LZ_FORMAT.md` `DEBUGGER_TRACE.md` `FINDINGS.md` | the container format and the live-tracing method |
| `CHANGELOG.md` | every build, what changed, and what broke |

## The interesting parts

**`tools/banlz.py`** — a clean-room implementation of the game's LZ variant
(compressor and decompressor), which is what makes everything else possible.

**The verifiers.** Each exists because something shipped broken:

| Tool | Catches |
|---|---|
| `verify_pointers.py` | edits that move bytes inside a record and orphan its pointer table |
| `verify_elf_patches.py` | ELF patches that silently reverted |
| `verify_spirits.py` | two spirit commands sharing one name |
| `scan_visible_defects.py` | anything a player would see: overflow, untranslated lines, escapes, garbage tails |
| `zkn_name_check.py` | library names that disagree with the glossary |
| `fix_dead_links.py` | `《term》` links with no keyword-bank entry — these CRASH the scene |

**`analysis/glossary_sources.json`** — every name records where it came from and
how far to trust it: `cited` (a named source), `corrected`, `chosen` (no official
English exists), `corroborated` (matches our own script — which is circular, not
evidence), `legacy-unverified` (inherited, source unrecorded), `ambiguous` (the
same katakana is two different characters — never rename globally).

## Lessons that cost the most

Written up properly in `docs/TECHNICAL.md`; the short version:

- **A glossary term and its `《》` links are ONE edit.** Renaming either half
  alone leaves a dead link, and a dead link crashes the scene. Rename the bank
  first: an entry with no incoming links is harmless, a link with no entry is not.
- **In-place edits must preserve every offset in the record.** Rewriting a
  record as `"\x00".join(parts)` after shortening a string slides everything
  after it left while the pointer table stays put. Record *length* is unchanged,
  so every length-based check still passes. The game boots, plays, and freezes
  when you load a save.
- **Name sources contradict each other**, including akurasu with itself. Fix a
  precedence order and follow it; a better-sourced spelling is still the wrong
  one if it is not the project's baseline.
- **A tool being correct is not evidence that its output shipped.** Two bugs here
  were "the fix existed and never reached the image". Verify against the image.

## What is deliberately not here

Nothing that is Banpresto's or Bandai's:

- no disc images, `.bin`, `.cue` or `.chd`
- no extracted game files, no `DATA_*.BIN`, no boot ELF
- no dumps of the original Japanese script
- seven working files were removed from `tools/` because they embedded blocks of
  the original dialogue verbatim

Also excluded: third-party binaries (`chdman`, `xdelta3`, MAME) — get those from
their own projects.

Short Japanese snippets do appear in docstrings and the changelog where they are
needed to explain a bug or a rule.

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
